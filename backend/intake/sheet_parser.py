"""Layout-aware Excel and CSV parser synthesis and validation."""
from __future__ import annotations
import csv
import hashlib
import json
import logging
from pathlib import Path
import re
import time
from pydantic import BaseModel
from backend import config
from backend.intake import sandbox
from backend.llm.client import call_json
from backend.llm.prompts import gen_sheet_parser
from backend.models import Evidence, ParserOut, Rule, Roster, Session
from backend.registry import db

log = logging.getLogger(__name__)

class ParseError(RuntimeError): pass

class IngestSheetResult(BaseModel):
    rules: list[Rule]
    cache_hit: bool
    attempts: int
    tokens_used: int
    seconds: float

def layout_signature(path: Path) -> str:
    path = Path(path)
    if path.suffix.lower() == ".csv":
        try:
            with path.open("r", encoding="utf-8", errors="replace") as f:
                reader = csv.reader(f)
                headers = []
                for row in reader:
                    vals = [str(v).strip().lower() for v in row if str(v).strip()]
                    if vals:
                        headers = vals
                        break
            layout = [["csv", headers]]
            return hashlib.sha256(json.dumps(layout, ensure_ascii=False, separators=(",", ":")).encode()).hexdigest()[:16]
        except Exception as exc:
            raise ParseError(f"Cannot read CSV file: {exc}") from exc

    try:
        import openpyxl
    except ImportError as exc:
        raise ParseError("Install openpyxl to read spreadsheets") from exc
    book = openpyxl.load_workbook(path, read_only=True, data_only=True)
    try:
        layout = []
        for sheet in book.worksheets:
            headers = []
            for row in sheet.iter_rows(min_row=1, max_row=10, values_only=True):
                vals = [str(v).strip().lower() for v in row if v is not None and str(v).strip()]
                if vals:
                    headers = vals
                    break
            layout.append([sheet.title, headers])
    finally:
        book.close()
    return hashlib.sha256(json.dumps(layout, ensure_ascii=False, separators=(",", ":")).encode()).hexdigest()[:16]

def _sample(path: Path) -> str:
    path = Path(path)
    if path.suffix.lower() == ".csv":
        lines = []
        with path.open("r", encoding="utf-8", errors="replace") as f:
            reader = csv.reader(f)
            for row_no, row in enumerate(reader, 1):
                if row_no > 10:
                    break
                lines.append(f"{row_no}: " + " | ".join(str(v).strip() for v in row))
        return "\n".join(lines)

    import openpyxl
    book = openpyxl.load_workbook(path, read_only=True, data_only=True)
    lines = []
    try:
        sheet = book.active
        for row_no, row in enumerate(sheet.iter_rows(min_row=1, max_row=10, values_only=True), 1):
            lines.append(f"{row_no}: " + " | ".join("" if v is None else str(v) for v in row))
    finally:
        book.close()
    return "\n".join(lines)

def _default_parser_code() -> str:
    return '''import pandas as pd
from pathlib import Path

def parse(path: str) -> list[dict]:
    p = Path(path)
    try:
        if p.suffix.lower() == ".csv":
            df = pd.read_csv(path)
        else:
            df = pd.read_excel(path, header=0)
    except Exception:
        df = pd.read_csv(path)
    out = []
    cols = [str(c).strip().lower() for c in df.columns]
    course_idx = 0
    faculty_idx = 1
    for i, c in enumerate(cols):
        if any(k in c for k in ["course", "subject", "session", "title", "class", "module"]):
            course_idx = i
        elif any(k in c for k in ["faculty", "teacher", "prof", "instructor", "staff", "qualified", "name"]):
            faculty_idx = i
    if course_idx == faculty_idx and len(cols) > 1:
        course_idx = 0
        faculty_idx = 1
    for r_idx, row in df.iterrows():
        c_val = str(row.iloc[course_idx]).strip() if len(row) > course_idx and pd.notna(row.iloc[course_idx]) else ""
        t_val = str(row.iloc[faculty_idx]).strip() if len(row) > faculty_idx and pd.notna(row.iloc[faculty_idx]) else ""
        if not c_val or c_val.lower() == "nan" or not t_val or t_val.lower() == "nan":
            continue
        teachers = [t.strip() for t in t_val.replace(";", ",").split(",") if t.strip()]
        if c_val and teachers:
            col_letter = chr(ord('A') + faculty_idx) if faculty_idx < 26 else 'B'
            out.append({
                "course": c_val,
                "teachers": teachers,
                "source_cell": f"{col_letter}{r_idx + 2}",
            })
    return out
'''

def _find_session(roster: Roster, course_name: str) -> Session | None:
    c_clean = course_name.strip().casefold()
    for s in roster.sessions:
        if s.course.strip().casefold() == c_clean or s.id.strip().casefold() == c_clean:
            return s
    for s in roster.sessions:
        s_title = s.course.strip().casefold()
        if s_title in c_clean or c_clean in s_title:
            return s
    c_tokens = set(re.findall(r"[a-z0-9]+", c_clean))
    for s in roster.sessions:
        s_tokens = set(re.findall(r"[a-z0-9]+", s.course.lower()))
        if c_tokens and (c_tokens.issubset(s_tokens) or s_tokens.issubset(c_tokens)):
            return s
    return None

def _source_values(path: Path) -> set[str]:
    """Cell values used to reject cached/generated parsers that invent entities."""
    if path.suffix.lower() == ".csv":
        with path.open(encoding="utf-8-sig", errors="replace", newline="") as handle:
            return {" ".join(cell.split()).casefold() for row in csv.reader(handle) for cell in row if cell.strip()}
    import openpyxl
    book = openpyxl.load_workbook(path, read_only=True, data_only=True)
    try:
        return {" ".join(str(cell).split()).casefold() for sheet in book for row in sheet.iter_rows(values_only=True) for cell in row if cell is not None}
    finally:
        book.close()


def _validated(rows: list[dict], roster: Roster, source_values: set[str] | None = None) -> tuple[list[tuple[str, list[str], str]], int]:
    roster_changed = False
    good = []
    failures = 0
    for row in rows:
        try:
            raw_course = row.get("course")
            raw_teachers = row.get("teachers")
            source_cell = row.get("source_cell", "A1")
            if not isinstance(raw_course, str) or not raw_course.strip():
                raise ValueError("missing course")
            if not isinstance(raw_teachers, list) or not raw_teachers:
                raise ValueError("missing teachers")

            course_clean = raw_course.strip()
            cleaned_teachers = [t.strip() for t in raw_teachers if isinstance(t, str) and t.strip()]
            if not cleaned_teachers:
                raise ValueError("empty teachers list")

            if source_values is not None:
                if " ".join(course_clean.split()).casefold() not in source_values:
                    raise ValueError("course is absent from the uploaded sheet")
                for teacher in cleaned_teachers:
                    normalized = " ".join(teacher.split()).casefold()
                    if not any(normalized in [part.strip() for part in re.split(r"[,;]|\band\b", cell)] for cell in source_values):
                        raise ValueError("teacher is absent from the uploaded sheet")

            # Ensure all teachers are registered in roster
            for t in cleaned_teachers:
                if t not in roster.teachers:
                    roster.teachers.append(t)
                    roster_changed = True

            session = _find_session(roster, course_clean)
            if session:
                for t in cleaned_teachers:
                    if t not in session.teachers:
                        session.teachers.append(t)
                        roster_changed = True
                session_id = session.id
            else:
                sid = re.sub(r"[^A-Za-z0-9]+", "_", course_clean.upper()).strip("_") or f"SES_{len(roster.sessions) + 1}"
                new_session = Session(id=sid, course=course_clean, teachers=cleaned_teachers, size=30)
                roster.sessions.append(new_session)
                roster_changed = True
                session_id = sid

            good.append((session_id, list(dict.fromkeys(cleaned_teachers)), str(source_cell)))
        except (KeyError, ValueError, TypeError):
            failures += 1

    if roster_changed:
        db.save_roster(roster)

    return good, failures

def ingest_sheet(path: Path, filename: str, roster: Roster | None = None) -> IngestSheetResult:
    start = time.monotonic()
    tokens_start = time.time()
    path = Path(path)
    if path.stat().st_size > 50 * 1024 * 1024:
        raise ParseError("Spreadsheet exceeds 50 MiB")
    roster = roster or db.get_roster()
    source_values = _source_values(path)
    sig = layout_signature(path)
    code = db.get_parser(sig)
    cache_hit = code is not None
    attempts = 0
    last_error = ""

    if code:
        try:
            rows = sandbox.run_parser(code, path)
            good, failed = _validated(rows, roster, source_values)
            if not good or (failed / len(rows) > 0.05):
                raise ParseError("cached parser output did not validate")
        except Exception as exc:
            db.delete_parser(sig)
            code = None
            cache_hit = False
            last_error = str(exc)

    if code is None:
        # Synthesis phase using Gemma 12B reasoning tier
        for attempt in range(1, 4):
            attempts = attempt
            try:
                sample_text = _sample(path)
                generated = call_json(
                    fn="gen_sheet_parser",
                    tier="reason",
                    messages=[
                        {"role": "system", "content": "Return a standalone Python parser as JSON."},
                        {"role": "user", "content": gen_sheet_parser(sample_text, last_error)},
                    ],
                    schema=ParserOut,
                    retries=1,
                    timeout_s=config.LLM_TIMEOUT_S,
                    options={"num_predict": 2200, "temperature": 0.1, "think": False},
                    fallback_to_mock=False,
                )
                candidate_code = generated.code
                rows = sandbox.run_parser(candidate_code, path)
                good, failed = _validated(rows, roster, source_values)
                if rows and good and (failed / len(rows) <= 0.05):
                    code = candidate_code
                    db.save_parser(sig, code)
                    break
            except Exception as exc:
                last_error = str(exc)

        # Fallback to deterministic parser if 12B synthesis was unavailable or failed
        if code is None:
            try:
                candidate_code = _default_parser_code()
                rows = sandbox.run_parser(candidate_code, path)
                good, failed = _validated(rows, roster, source_values)
                if rows and good and (failed / len(rows) <= 0.05):
                    code = candidate_code
                    db.save_parser(sig, code)
            except Exception as exc:
                last_error = f"{last_error}; fallback error: {exc}"

        if code is None:
            raise ParseError(f"Could not parse spreadsheet after {attempts} attempts: {last_error}")

    if not rows or not good or (failed / len(rows) > 0.05):
        raise ParseError(f"{failed} of {len(rows)} rows failed validation")

    rules = []
    for sid, names, cell in good:
        rule = Rule(
            id=db.next_rule_id(),
            type="only_qualified",
            params={"session_id": sid, "teachers": names},
            owner="Dean",
            evidence=[Evidence(kind="sheet", ref=f"{Path(filename).name}!{cell}")],
        )
        db.save_rule(rule)
        rules.append(rule)

    return IngestSheetResult(
        rules=rules,
        cache_hit=cache_hit,
        attempts=attempts,
        tokens_used=db.tokens_since(tokens_start),
        seconds=time.monotonic() - start,
    )

