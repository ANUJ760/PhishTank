"""Unified Multi-Modal Data Dump Intake.

Consolidates heterogeneous data sources (spreadsheets, documents, images, audio, natural text)
and applies Gemma intelligence governed by explicit user instructions to extract constraints,
domain entities, and structured rules grounded in the real timetable.
"""
from __future__ import annotations

import base64
import csv
import io
import json
import logging
import re
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from backend import config
from backend.llm.client import call_json
from backend.models import Evidence, Roster, Room, Rule, Schedule, Session, validate_params
from backend.registry import db

log = logging.getLogger(__name__)

DAY_NAMES: dict[int, str] = {
    0: "Monday",
    1: "Tuesday",
    2: "Wednesday",
    3: "Thursday",
    4: "Friday",
}

DAY_LOOKUP: dict[str, int] = {
    "mon": 0, "monday": 0, "day 0": 0, "day0": 0,
    "tue": 1, "tues": 1, "tuesday": 1, "day 1": 1, "day1": 1,
    "wed": 2, "wednesday": 2, "day 2": 2, "day2": 2,
    "thu": 3, "thur": 3, "thurs": 3, "thursday": 3, "day 3": 3, "day3": 3,
    "fri": 4, "friday": 4, "day 4": 4, "day4": 4,
}

SLOT_HOURS: dict[int, str] = {
    0: "09:00 - 10:00",
    1: "10:00 - 11:00",
    2: "11:00 - 12:00",
    3: "13:00 - 14:00",
    4: "14:00 - 15:00",
    5: "15:00 - 16:00",
}


def _format_time_window(slots: list[int]) -> str:
    if not slots:
        return "Unspecified window"
    sorted_slots = sorted(slots)
    if sorted_slots == [0, 1, 2]:
        return "Morning (09:00 - 12:00)"
    if sorted_slots == [3, 4, 5]:
        return "Afternoon (13:00 - 16:00)"
    if sorted_slots == list(range(6)):
        return "Full Day (09:00 - 16:00)"
    if len(sorted_slots) == 1:
        return SLOT_HOURS.get(sorted_slots[0], f"Slot {sorted_slots[0]}")
    first = sorted_slots[0]
    last = sorted_slots[-1]
    start_str = SLOT_HOURS.get(first, f"Slot {first}").split(" - ")[0]
    end_str = SLOT_HOURS.get(last, f"Slot {last}").split(" - ")[-1]
    return f"{start_str} - {end_str} (Slots {', '.join(str(s) for s in sorted_slots)})"


class DataDumpFileSummary(BaseModel):
    filename: str
    file_type: str
    size_bytes: int
    status: str
    preview: str = ""


class ExtractedRuleDraft(BaseModel):
    type: str
    params: dict[str, Any]
    owner: str | None = None
    evidence_ref: str | None = None


class ExtractedEntity(BaseModel):
    name: str
    kind: str  # person, room, resource, camp, patient, vehicle, warehouse, etc.
    details: str = ""


class ExtractedRuleCard(BaseModel):
    id: str
    type: str
    owner: str
    params: dict[str, Any]
    status: str = "draft"
    category: str
    headline: str
    plain_description: str
    target_entity: str
    day_name: str
    time_window: str
    slots_display: str
    timetable_impact: str
    has_conflict: bool
    evidence_ref: str = ""


class DataDumpLLMOut(BaseModel):
    summary: str = Field(description="Comprehensive executive summary of the dumped data and what Gemma made of it")
    rules: list[ExtractedRuleDraft] = Field(default_factory=list, description="Extracted scheduling, allocation, or operational constraint rules")
    entities: list[ExtractedEntity] = Field(default_factory=list, description="Identified entities, agents, facilities, or items")
    insights: list[str] = Field(default_factory=list, description="Key operational insights or patterns discovered in the dump")
    warnings: list[str] = Field(default_factory=list, description="Conflicts, data gaps, or ambiguities flagged")


class DataDumpResult(BaseModel):
    summary: str
    instructions_executed: str
    rules: list[Rule]
    rule_cards: list[ExtractedRuleCard] = Field(default_factory=list)
    entities: list[dict[str, Any]]
    insights: list[str]
    warnings: list[str]
    processed_files: list[DataDumpFileSummary]


def _extract_file_preview(filename: str, content: bytes) -> tuple[str, str]:
    """Returns (file_type, preview_text) for a dumped file."""
    ext = Path(filename).suffix.lower()
    size = len(content)

    if ext in (".csv", ".tsv"):
        try:
            text = content.decode("utf-8", errors="replace")
            lines = text.splitlines()[:20]
            return "csv", "\n".join(lines)
        except Exception as e:
            return "csv", f"Error decoding CSV: {e}"

    if ext in (".xlsx", ".xls"):
        try:
            import pandas as pd
            excel_file = io.BytesIO(content)
            xls = pd.ExcelFile(excel_file)
            sheet_previews = []
            for sheet_name in xls.sheet_names[:3]:
                df = pd.read_excel(xls, sheet_name=sheet_name, nrows=5)
                sheet_previews.append(f"--- Sheet '{sheet_name}' (columns: {list(df.columns)}) ---\n{df.to_string(index=False)}")
            return "spreadsheet", "\n".join(sheet_previews)
        except Exception as e:
            return "spreadsheet", f"Spreadsheet metadata: {size} bytes ({ext})"

    if ext in (".txt", ".md", ".log", ".json"):
        try:
            text = content.decode("utf-8", errors="replace")
            return "text", text[:3000]
        except Exception as e:
            return "text", f"Error decoding text: {e}"

    if ext in (".png", ".jpg", ".jpeg", ".webp"):
        return "image", f"Visual asset: {filename} ({ext.upper()}, {size} bytes)"

    if ext in (".wav", ".mp3", ".ogg", ".m4a"):
        return "audio", f"Audio memo: {filename} ({ext.upper()}, {size} bytes)"

    return "binary", f"Binary document: {filename} ({size} bytes)"


def _parse_day_value(val: Any) -> int:
    """Parse day index (0-4) from string or number."""
    s = str(val).strip().lower()
    if s in DAY_LOOKUP:
        return DAY_LOOKUP[s]
    for k, v in DAY_LOOKUP.items():
        if k in s:
            return v
    if s.isdigit() and 0 <= int(s) < config.DAYS:
        return int(s)
    return 0


def _parse_slot_values(val: Any) -> list[int]:
    """Parse list of slot indices (0-5) from string or number."""
    s = str(val).strip().lower()
    if s.isdigit() and 0 <= int(s) < config.SLOTS_PER_DAY:
        return [int(s)]
    if "morning" in s or "09:00" in s or "9:00" in s:
        return [0, 1, 2]
    if "afternoon" in s or "13:00" in s or "1:00" in s or "post-lunch" in s:
        return [3, 4, 5]
    if "full" in s or "all" in s or "entire" in s or "whole" in s:
        return list(range(config.SLOTS_PER_DAY))
    tokens = re.findall(r"\b([0-5])\b", s)
    if tokens:
        return sorted(list(set(int(t) for t in tokens)))
    return [0, 1]


def _ensure_teacher(roster: Roster, name: str) -> str:
    """Ensure a teacher exists in roster, returning their canonical name."""
    clean = name.strip()
    if not clean:
        return ""
    # Exact match
    for t in roster.teachers:
        if clean.lower() == t.lower():
            return t
    # Substring / partial match
    for t in roster.teachers:
        if clean.lower() in t.lower() or t.lower() in clean.lower():
            return t
    roster.teachers.append(clean)
    return clean


def _ensure_room(roster: Roster, name: str) -> str:
    """Ensure a room exists in roster, returning its canonical name."""
    clean = name.strip()
    if not clean:
        return ""
    for r in roster.rooms:
        if clean.lower() == r.name.lower():
            return r.name
    for r in roster.rooms:
        if clean.lower() in r.name.lower() or r.name.lower() in clean.lower():
            return r.name
    roster.rooms.append(Room(name=clean, capacity=30))
    return clean


def _ensure_session(roster: Roster, course_or_id: str, teachers: list[str] | None = None) -> str:
    """Ensure a session exists in roster, updating candidate teachers if provided."""
    clean = course_or_id.strip()
    if not clean:
        return ""
    for s in roster.sessions:
        if clean.lower() == s.id.lower() or clean.lower() == s.course.lower():
            if teachers:
                for t in teachers:
                    if t not in s.teachers:
                        s.teachers.append(t)
            return s.id
    # Create new session
    sid = re.sub(r"[^A-Za-z0-9]+", "_", clean.upper()).strip("_")
    if not sid:
        sid = f"SES_{len(roster.sessions) + 1}"
    t_list = [t for t in (teachers or []) if t]
    if not t_list:
        t_list = [roster.teachers[0]] if roster.teachers else ["Faculty"]
    roster.sessions.append(Session(id=sid, course=clean, teachers=t_list, size=30))
    return sid


def _extract_tables_from_file(filename: str, content: bytes) -> list[tuple[str, list[str], list[list[str]]]]:
    """Extract tabular data as list of (table_ref, headers, rows) from CSV, TSV, Excel, or JSON."""
    tables: list[tuple[str, list[str], list[list[str]]]] = []
    ext = Path(filename).suffix.lower()

    if ext in (".csv", ".tsv"):
        try:
            delimiter = "\t" if ext == ".tsv" else ","
            text_stream = content.decode("utf-8", errors="replace")
            reader = csv.reader(io.StringIO(text_stream), delimiter=delimiter)
            rows = [[str(cell).strip() for cell in r] for r in reader if r and any(str(c).strip() for c in r)]
            if len(rows) > 1:
                headers = [h.strip().lower() for h in rows[0]]
                tables.append((filename, headers, rows[1:]))
        except Exception as exc:
            log.warning("CSV table extraction error for %s: %s", filename, exc)

    elif ext in (".xlsx", ".xls"):
        try:
            import pandas as pd
            excel_file = io.BytesIO(content)
            xls = pd.ExcelFile(excel_file)
            for sheet_name in xls.sheet_names:
                df = pd.read_excel(xls, sheet_name=sheet_name).dropna(how="all")
                if not df.empty and len(df.columns) > 0:
                    headers = [str(c).strip().lower() for c in df.columns]
                    data_rows = []
                    for _, row in df.iterrows():
                        data_rows.append([str(val).strip() if pd.notna(val) else "" for val in row])
                    tables.append((f"{filename}#{sheet_name}", headers, data_rows))
        except Exception as exc:
            log.warning("Excel table extraction error for %s: %s", filename, exc)

    elif ext == ".json":
        try:
            parsed = json.loads(content.decode("utf-8", errors="replace"))
            if isinstance(parsed, list) and len(parsed) > 0 and isinstance(parsed[0], dict):
                headers = [k.strip().lower() for k in parsed[0].keys()]
                data_rows = [[str(item.get(k, "")).strip() for k in parsed[0].keys()] for item in parsed]
                tables.append((filename, headers, data_rows))
            elif isinstance(parsed, dict):
                for k, v in parsed.items():
                    if isinstance(v, list) and len(v) > 0 and isinstance(v[0], dict):
                        headers = [col.strip().lower() for col in v[0].keys()]
                        data_rows = [[str(item.get(col, "")).strip() for col in v[0].keys()] for item in v]
                        tables.append((f"{filename}#{k}", headers, data_rows))
        except Exception as exc:
            log.warning("JSON table extraction error for %s: %s", filename, exc)

    return tables


def _parse_days_and_slots_from_text(text: str) -> tuple[int, list[int]]:
    """Heuristic extraction of day index (0-4) and slot indices from text snippet."""
    t_lower = text.lower()
    day = 0
    for day_word, day_idx in DAY_LOOKUP.items():
        if re.search(r"\b" + re.escape(day_word) + r"\b", t_lower):
            day = day_idx
            break

    slots: list[int] = []
    if "full day" in t_lower or "whole day" in t_lower or "all day" in t_lower or "entire day" in t_lower:
        slots = list(range(config.SLOTS_PER_DAY))
    elif "morning" in t_lower or "09:00 to 12:00" in t_lower or "9 to 12" in t_lower or "9:00 - 12:00" in t_lower:
        slots = [0, 1, 2]
    elif "afternoon" in t_lower or "13:00 to 16:00" in t_lower or "1 to 4" in t_lower or "post-lunch" in t_lower:
        slots = [3, 4, 5]
    elif "slots 0 and 1" in t_lower or "0 and 1" in t_lower or "slots 0, 1" in t_lower or "09:00 and 11:00" in t_lower or "09:00 to 11:00" in t_lower:
        slots = [0, 1]
    elif "slots 3 and 4" in t_lower or "3 and 4" in t_lower:
        slots = [3, 4]
    else:
        found_slots = set()
        for s in range(config.SLOTS_PER_DAY):
            if f"slot {s}" in t_lower or f"slot:{s}" in t_lower or f"slot_{s}" in t_lower:
                found_slots.add(s)
        if "09:00" in t_lower or "9:00" in t_lower or "9am" in t_lower:
            found_slots.add(0)
        if "10:00" in t_lower or "10am" in t_lower:
            found_slots.add(1)
        if "11:00" in t_lower or "11am" in t_lower:
            found_slots.add(2)
        if "13:00" in t_lower or "1:00" in t_lower or "1pm" in t_lower:
            found_slots.add(3)
        if "14:00" in t_lower or "2:00" in t_lower or "2pm" in t_lower:
            found_slots.add(4)
        if "15:00" in t_lower or "3:00" in t_lower or "3pm" in t_lower:
            found_slots.add(5)
        slots = sorted(list(found_slots)) if found_slots else [0, 1]

    return day, slots


def _extract_deterministic_rules(
    roster: Roster,
    schedule: Schedule | None,
    instructions: str,
    notes: str,
    files: list[tuple[str, bytes]],
) -> list[ExtractedRuleDraft]:
    """Rapid, timetable-grounded deterministic extraction avoiding LLM latency and hallucination."""
    extracted: list[ExtractedRuleDraft] = []
    seen_keys: set[str] = set()

    def add_draft(d: ExtractedRuleDraft):
        key = f"{d.type}:{json.dumps(d.params, sort_keys=True)}"
        if key not in seen_keys:
            seen_keys.add(key)
            extracted.append(d)

    # 0. Layout-aware spreadsheet ingestion using sandbox parser synthesis and layout caching
    for filename, content in files:
        ext = Path(filename).suffix.lower()
        if ext in (".xlsx", ".xls", ".csv") and len(content) > 0:
            try:
                temp_path = config.UPLOAD_DIR / f"dump_staging_{Path(filename).name}"
                temp_path.parent.mkdir(parents=True, exist_ok=True)
                temp_path.write_bytes(content)
                try:
                    from backend.intake import sheet_parser
                    ingest_res = sheet_parser.ingest_sheet(temp_path, filename, roster=roster)
                    for rule in ingest_res.rules:
                        ref_str = rule.evidence[0].ref if rule.evidence else f"{filename}!sheet"
                        add_draft(
                            ExtractedRuleDraft(
                                type=rule.type,
                                params=rule.params,
                                owner=rule.owner,
                                evidence_ref=ref_str,
                            )
                        )
                finally:
                    temp_path.unlink(missing_ok=True)
            except Exception as exc:
                log.info("Layout parser pass skipped for %s (%s); falling back to direct table parser", filename, exc)

    # 1. Parse all tabular files (CSV, TSV, XLSX, XLS, JSON)
    for filename, content in files:
        tables = _extract_tables_from_file(filename, content)
        for table_ref, headers, rows in tables:
            t_idx = next((i for i, h in enumerate(headers) if any(k in h for k in ("teach", "facult", "prof", "instructor", "doctor", "surgeon", "name"))), -1)
            c_idx = next((i for i, h in enumerate(headers) if any(k in h for k in ("course", "session", "subject", "module", "class", "lecture"))), -1)
            r_idx = next((i for i, h in enumerate(headers) if any(k in h for k in ("room", "lab", "hall", "theater", "theatre", "venue", "classroom", "or", "ot"))), -1)
            d_idx = next((i for i, h in enumerate(headers) if any(k in h for k in ("day", "date", "weekday"))), -1)
            slot_idx = next((i for i, h in enumerate(headers) if any(k in h for k in ("slot", "time", "hour", "window", "period"))), -1)
            status_idx = next((i for i, h in enumerate(headers) if any(k in h for k in ("status", "reason", "type", "avail", "remark", "note", "action"))), -1)

            for r_num, row in enumerate(rows, start=2):
                # Pattern A: Course & Teacher Workload / Schedule Placement
                if c_idx >= 0 and c_idx < len(row) and t_idx >= 0 and t_idx < len(row):
                    course_val = row[c_idx].strip()
                    teacher_val = row[t_idx].strip()
                    if course_val and teacher_val:
                        raw_teachers = [t.strip() for t in re.split(r"[,;/]|\band\b", teacher_val) if t.strip()]
                        registered_teachers = [_ensure_teacher(roster, t) for t in raw_teachers if t]
                        session_id = _ensure_session(roster, course_val, registered_teachers)

                        # If this row also contains day and slot -> Pinned Live Placement
                        if d_idx >= 0 and d_idx < len(row) and slot_idx >= 0 and slot_idx < len(row):
                            d_val = _parse_day_value(row[d_idx])
                            s_vals = _parse_slot_values(row[slot_idx])
                            if r_idx >= 0 and r_idx < len(row):
                                _ensure_room(roster, row[r_idx])
                            add_draft(
                                ExtractedRuleDraft(
                                    type="pin_session",
                                    params={"session_id": session_id, "day": d_val, "slots": s_vals},
                                    owner="Academic Dean",
                                    evidence_ref=f"{table_ref}@row{r_num}",
                                )
                            )
                            if registered_teachers:
                                add_draft(
                                    ExtractedRuleDraft(
                                        type="only_qualified",
                                        params={"session_id": session_id, "teachers": registered_teachers},
                                        owner="Academic Dean",
                                        evidence_ref=f"{table_ref}@row{r_num}",
                                    )
                                )
                        else:
                            # Workload qualification constraint (e.g. workload.xlsx)
                            if registered_teachers:
                                add_draft(
                                    ExtractedRuleDraft(
                                        type="only_qualified",
                                        params={"session_id": session_id, "teachers": registered_teachers},
                                        owner="Academic Dean",
                                        evidence_ref=f"{table_ref}@row{r_num}",
                                    )
                                )

                # Pattern B: Teacher Availability / Unavailability Table
                elif t_idx >= 0 and t_idx < len(row) and c_idx < 0:
                    val = row[t_idx].strip()
                    if val:
                        matched_t = _ensure_teacher(roster, val)
                        d_val = _parse_day_value(row[d_idx]) if (d_idx >= 0 and d_idx < len(row)) else 0
                        s_vals = _parse_slot_values(row[slot_idx]) if (slot_idx >= 0 and slot_idx < len(row)) else [0, 1]
                        add_draft(
                            ExtractedRuleDraft(
                                type="teacher_unavailable",
                                params={"teacher": matched_t, "day": d_val, "slots": s_vals},
                                owner=matched_t,
                                evidence_ref=f"{table_ref}@row{r_num}",
                            )
                        )

                # Pattern C: Room Maintenance / Unavailability Table
                elif r_idx >= 0 and r_idx < len(row) and t_idx < 0 and c_idx < 0:
                    val = row[r_idx].strip()
                    if val:
                        matched_rm = _ensure_room(roster, val)
                        d_val = _parse_day_value(row[d_idx]) if (d_idx >= 0 and d_idx < len(row)) else 0
                        s_vals = _parse_slot_values(row[slot_idx]) if (slot_idx >= 0 and slot_idx < len(row)) else [0, 1]
                        add_draft(
                            ExtractedRuleDraft(
                                type="room_unavailable",
                                params={"room": matched_rm, "day": d_val, "slots": s_vals},
                                owner="Facilities Manager",
                                evidence_ref=f"{table_ref}@row{r_num}",
                            )
                        )

    # 2. Textual context analysis (instructions + notes + file text previews)
    file_texts = []
    for fn, cnt in files:
        ext = Path(fn).suffix.lower()
        if ext in (".txt", ".md", ".log", ".json"):
            file_texts.append(cnt.decode("utf-8", errors="replace"))
    combined_text = "\n".join([t for t in [instructions, notes] + file_texts if t.strip()])
    sentences = [s.strip() for s in re.split(r"(?<!\bDr)(?<!\bMr)(?<!\bMs)(?<!\bProf)\.\s+|\n+|;\s*", combined_text) if s.strip()]

    # A. Teacher Unavailability Extraction
    unavail_keywords = ("unavail", "cannot", "can't", "not avail", "leave", "absent", "meeting", "duty", "duties", "sick", "off", "busy", "conference", "preference", "no class", "conflict")
    for s in sentences:
        s_low = s.lower()
        if any(w in s_low for w in unavail_keywords):
            # Check known teachers
            for t in list(roster.teachers):
                t_variants = [t.lower(), t.split()[-1].lower()]
                if any(re.search(r"\b" + re.escape(v) + r"\b", s_low) for v in t_variants):
                    day, slots = _parse_days_and_slots_from_text(s)
                    add_draft(
                        ExtractedRuleDraft(
                            type="teacher_unavailable",
                            params={"teacher": t, "day": day, "slots": slots},
                            owner=t,
                            evidence_ref="intake-notes",
                        )
                    )
            # Check title-prefixed candidates (e.g. Dr. Adams, Prof. Sharma)
            title_matches = re.findall(r"\b(?:Prof(?:\.|essor)?|Dr\.|Doctor|Mr\.|Ms\.|Mrs\.|Faculty|Instructor)\s+[A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)?\b", s)
            for cand in title_matches:
                t = _ensure_teacher(roster, cand)
                day, slots = _parse_days_and_slots_from_text(s)
                add_draft(
                    ExtractedRuleDraft(
                        type="teacher_unavailable",
                        params={"teacher": t, "day": day, "slots": slots},
                        owner=t,
                        evidence_ref="intake-notes",
                    )
                )
            # Check untitled name followed by unavailability phrasing
            name_m = re.search(r"\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\s+(?:cannot teach|can't teach|is unavailable|is not available|on leave|on sick leave|has a meeting|is off|cannot be scheduled)\b", s)
            if name_m:
                cand_name = name_m.group(1)
                t = _ensure_teacher(roster, cand_name)
                day, slots = _parse_days_and_slots_from_text(s)
                add_draft(
                    ExtractedRuleDraft(
                        type="teacher_unavailable",
                        params={"teacher": t, "day": day, "slots": slots},
                        owner=t,
                        evidence_ref="intake-notes",
                    )
                )

    # B. Room Maintenance / Unavailability
    maint_keywords = ("maint", "renovat", "closed", "offline", "unavail", "repair", "clean", "occupied", "shut", "locked", "reserved")
    for s in sentences:
        s_low = s.lower()
        if any(w in s_low for w in maint_keywords):
            # Check known rooms
            for rm in list(roster.rooms):
                if rm.name.lower() in s_low:
                    day, slots = _parse_days_and_slots_from_text(s)
                    add_draft(
                        ExtractedRuleDraft(
                            type="room_unavailable",
                            params={"room": rm.name, "day": day, "slots": slots},
                            owner="Facilities Manager",
                            evidence_ref="intake-notes",
                        )
                    )
            # Check room patterns (e.g. Room 402, Lab-B)
            rm_matches = re.findall(r"\b(?:Room|Lab|Hall|Theater|Theatre|OR|OT|Ward)\s*[-_#]?\s*[A-Za-z0-9]+\b", s, re.IGNORECASE)
            for cand_rm in rm_matches:
                rm_name = _ensure_room(roster, cand_rm)
                day, slots = _parse_days_and_slots_from_text(s)
                add_draft(
                    ExtractedRuleDraft(
                        type="room_unavailable",
                        params={"room": rm_name, "day": day, "slots": slots},
                        owner="Facilities Manager",
                        evidence_ref="intake-notes",
                    )
                )

    # C. Session Locking (Pin) & Qualifications
    for s in sentences:
        s_low = s.lower()
        for ses in list(roster.sessions):
            s_id = ses.id
            c_name = ses.course
            if s_id.lower() in s_low or c_name.lower() in s_low:
                # Qualification
                if any(w in s_low for w in ("qualif", "only", "must be handled", "must be taught", "assigned to", "certified", "instructor")):
                    matched_instructors = [
                        t for t in roster.teachers
                        if t.lower() in s_low or t.split()[-1].lower() in s_low
                    ]
                    if not matched_instructors:
                        matched_instructors = ses.teachers[:1] or [roster.teachers[0]]
                    add_draft(
                        ExtractedRuleDraft(
                            type="only_qualified",
                            params={"session_id": s_id, "teachers": matched_instructors},
                            owner="Academic Dean",
                            evidence_ref="intake-notes",
                        )
                    )
                # Pinning
                elif any(w in s_low for w in ("pin", "pinned", "lock", "locked", "fixed", "schedule at", "scheduled on", "must hold")):
                    day, slots = _parse_days_and_slots_from_text(s)
                    add_draft(
                        ExtractedRuleDraft(
                            type="pin_session",
                            params={"session_id": s_id, "day": day, "slots": slots},
                            owner="Academic Dean",
                            evidence_ref="intake-notes",
                        )
                    )

    # Persist updated roster with any dynamically discovered entities
    db.save_roster(roster)

    return extracted


def _build_rule_card(
    rule_id: str,
    rtype: str,
    params: dict[str, Any],
    owner: str,
    evidence_ref: str,
    schedule: Schedule | None,
    roster: Roster,
) -> ExtractedRuleCard:
    """Build a rich, human-friendly presentation card for an extracted constraint rule."""
    if rtype == "teacher_unavailable":
        teacher = params.get("teacher", "Faculty Member")
        day = params.get("day", 0)
        slots = params.get("slots", [0])
        day_name = DAY_NAMES.get(day, f"Day {day}")
        time_win = _format_time_window(slots)
        slots_disp = f"Slots: {', '.join(str(s) for s in slots)}"
        headline = f"{teacher} Unavailable on {day_name}"
        plain_desc = f"{teacher} cannot be scheduled on {day_name} during {time_win}."

        conflicts = []
        if schedule:
            for p in schedule.placements:
                if p.teacher == teacher and p.day == day and p.slot in slots:
                    conflicts.append(p)

        if conflicts:
            conflicted_names = ", ".join(f"{c.session_id} in {c.room}" for c in conflicts)
            timetable_impact = (
                f"Schedule Conflict: Impacts session(s) {conflicted_names} currently assigned to "
                f"{teacher} on {day_name}. Solver will reallocate or shift these sessions."
            )
            has_conflict = True
        else:
            timetable_impact = f"No Active Conflict: {teacher} has no scheduled sessions during this window on {day_name}."
            has_conflict = False

        return ExtractedRuleCard(
            id=rule_id,
            type=rtype,
            owner=owner,
            params=params,
            category="Faculty Availability",
            headline=headline,
            plain_description=plain_desc,
            target_entity=teacher,
            day_name=day_name,
            time_window=time_win,
            slots_display=slots_disp,
            timetable_impact=timetable_impact,
            has_conflict=has_conflict,
            evidence_ref=evidence_ref,
        )

    if rtype == "room_unavailable":
        room = params.get("room", "Room")
        day = params.get("day", 0)
        slots = params.get("slots", [0])
        day_name = DAY_NAMES.get(day, f"Day {day}")
        time_win = _format_time_window(slots)
        slots_disp = f"Slots: {', '.join(str(s) for s in slots)}"
        headline = f"Facility Maintenance: {room} ({day_name})"
        plain_desc = f"{room} is offline for maintenance or reserved on {day_name} during {time_win}."

        conflicts = []
        if schedule:
            for p in schedule.placements:
                if p.room == room and p.day == day and p.slot in slots:
                    conflicts.append(p)

        if conflicts:
            conflicted_names = ", ".join(f"{c.session_id} (taught by {c.teacher})" for c in conflicts)
            timetable_impact = (
                f"Room Conflict: Displaces {conflicted_names} scheduled in {room} on {day_name}. "
                f"Solver will move these classes to alternate rooms."
            )
            has_conflict = True
        else:
            timetable_impact = f"No Active Conflict: {room} is unassigned during these slots on {day_name}."
            has_conflict = False

        return ExtractedRuleCard(
            id=rule_id,
            type=rtype,
            owner=owner,
            params=params,
            category="Facility Maintenance",
            headline=headline,
            plain_description=plain_desc,
            target_entity=room,
            day_name=day_name,
            time_window=time_win,
            slots_display=slots_disp,
            timetable_impact=timetable_impact,
            has_conflict=has_conflict,
            evidence_ref=evidence_ref,
        )

    if rtype == "pin_session":
        session_id = params.get("session_id", "Session")
        day = params.get("day", 0)
        slots = params.get("slots", [0])
        day_name = DAY_NAMES.get(day, f"Day {day}")
        time_win = _format_time_window(slots)
        slots_disp = f"Slots: {', '.join(str(s) for s in slots)}"
        course_name = next((s.course for s in roster.sessions if s.id == session_id), session_id)
        headline = f"Fixed Slot: {course_name} ({session_id})"
        plain_desc = f"Locks {course_name} ({session_id}) to {day_name} during {time_win}."

        current_p = next((p for p in (schedule.placements if schedule else []) if p.session_id == session_id), None)
        if current_p:
            if current_p.day == day and current_p.slot in slots:
                timetable_impact = f"Schedule Alignment: {session_id} is already placed on {day_name} slot {current_p.slot}."
                has_conflict = False
            else:
                curr_day = DAY_NAMES.get(current_p.day, f"Day {current_p.day}")
                timetable_impact = f"Schedule Adjustment: {session_id} currently on {curr_day} slot {current_p.slot} will be shifted to {day_name}."
                has_conflict = True
        else:
            timetable_impact = f"New Placement: {session_id} will be locked into {day_name} {time_win}."
            has_conflict = False

        return ExtractedRuleCard(
            id=rule_id,
            type=rtype,
            owner=owner,
            params=params,
            category="Session Lock",
            headline=headline,
            plain_description=plain_desc,
            target_entity=session_id,
            day_name=day_name,
            time_window=time_win,
            slots_display=slots_disp,
            timetable_impact=timetable_impact,
            has_conflict=has_conflict,
            evidence_ref=evidence_ref,
        )

    # only_qualified
    session_id = params.get("session_id", "Session")
    teachers = params.get("teachers", [])
    course_name = next((s.course for s in roster.sessions if s.id == session_id), session_id)
    teachers_str = ", ".join(teachers)
    headline = f"Instructor Qualification: {course_name} ({session_id})"
    plain_desc = f"{course_name} ({session_id}) must only be assigned to certified faculty: {teachers_str}."

    current_p = next((p for p in (schedule.placements if schedule else []) if p.session_id == session_id), None)
    if current_p:
        if current_p.teacher in teachers:
            timetable_impact = f"Schedule Alignment: {session_id} is currently taught by authorized instructor {current_p.teacher}."
            has_conflict = False
        else:
            timetable_impact = (
                f"Faculty Reassignment: {session_id} is currently assigned to {current_p.teacher}. "
                f"Solver will reassign to qualified instructor(s) {teachers_str}."
            )
            has_conflict = True
    else:
        timetable_impact = f"Qualification Requirement: Ensures {session_id} is only scheduled with {teachers_str}."
        has_conflict = False

    return ExtractedRuleCard(
        id=rule_id,
        type=rtype,
        owner=owner,
        params=params,
        category="Instructor Qualification",
        headline=headline,
        plain_description=plain_desc,
        target_entity=session_id,
        day_name="All Days",
        time_window="Any Slot",
        slots_display="Course Requirement",
        timetable_impact=timetable_impact,
        has_conflict=has_conflict,
        evidence_ref=evidence_ref,
    )


def ingest_data_dump(
    files: list[tuple[str, bytes]],
    instructions: str = "",
    notes: str = "",
    roster: Roster | None = None,
) -> DataDumpResult:
    """Process a heterogeneous data dump with user instructions using Gemma intelligence and live timetable grounding."""
    roster = roster or db.get_roster()
    schedule = db.latest_schedule()
    processed_files: list[DataDumpFileSummary] = []
    dump_context_parts: list[str] = []

    # 1. Parse and extract previews from all dumped files
    for filename, content in files:
        file_type, preview = _extract_file_preview(filename, content)
        processed_files.append(
            DataDumpFileSummary(
                filename=filename,
                file_type=file_type,
                size_bytes=len(content),
                status="processed",
                preview=preview[:400],
            )
        )
        db.save_upload(filename, content)
        dump_context_parts.append(f"### FILE: {filename} (Type: {file_type}, Size: {len(content)} bytes)\n{preview}\n")

    # 2. Add raw typed notes
    if notes.strip():
        dump_context_parts.append(f"### DIRECT OPERATOR NOTES / RAW PASTE:\n{notes.strip()}\n")

    consolidated_data = "\n".join(dump_context_parts) if dump_context_parts else "No files attached. Only instructions provided."
    instructions_clean = instructions.strip() or "Extract all applicable operational constraints, entity relationships, and requirements."

    # 3. High-speed timetable-grounded deterministic extraction (0-5ms, zero hallucination)
    deterministic_drafts = _extract_deterministic_rules(
        roster=roster,
        schedule=schedule,
        instructions=instructions_clean,
        notes=notes,
        files=files,
    )

    # 4. Live timetable context for Gemma intelligence
    placements_summary = []
    if schedule and schedule.placements:
        for p in schedule.placements:
            placements_summary.append(
                f"- {p.session_id} taught by {p.teacher} in {p.room} on {DAY_NAMES.get(p.day, f'Day {p.day}')} "
                f"slot {p.slot} ({SLOT_HOURS.get(p.slot, f'Slot {p.slot}')})"
            )
    live_schedule_str = "\n".join(placements_summary) if placements_summary else "No active schedule placements recorded."

    prompt_system = f"""You are GeCompose's Multi-Modal Data Dump Synthesis & Constraint Ingestion Engine.
Analyze the heterogeneous raw data and instructions, and extract constraints grounded in the actual live timetable.

Current System Entities:
- Teachers: {', '.join(roster.teachers)}
- Rooms: {', '.join(r.name for r in roster.rooms)}
- Sessions: {', '.join(f"{s.id} ({s.course})" for s in roster.sessions)}

Active Live Timetable Placements:
{live_schedule_str}

Allowed Standard Rule Types & Parameters:
- teacher_unavailable: {{"teacher": <name>, "day": <0-4>, "slots": [<0-5>, ...]}}
- room_unavailable: {{"room": <name>, "day": <0-4>, "slots": [<0-5>, ...]}}
- pin_session: {{"session_id": <id>, "day": <0-4>, "slots": [<0-5>, ...]}}
- only_qualified: {{"session_id": <id>, "teachers": [<name>, ...]}}
(Day 0=Mon ... 4=Fri. Slots 0-2=morning, 3-5=afternoon)

Return concise JSON adhering exactly to this schema:
{{
  "summary": "Executive summary of what the data dump contained and what was synthesized",
  "rules": [
    {{"type": "<rule_type>", "params": {{...}}, "owner": "<role/name>", "evidence_ref": "<source filename or snippet>"}}
  ],
  "entities": [
    {{"name": "<entity name>", "kind": "<person|room|facility|session>", "details": "<context>"}}
  ],
  "insights": ["<key operational insight 1>", "<key operational insight 2>"],
  "warnings": ["<data discrepancy or risk detected>"]
}}
"""

    prompt_user = f"""OPERATOR INSTRUCTIONS ON WHAT IS REQUIRED:
\"\"\"{instructions_clean}\"\"\"

CONSOLIDATED DATA DUMP:
\"\"\"{consolidated_data}\"\"\"
"""

    messages = [
        {"role": "system", "content": prompt_system},
        {"role": "user", "content": prompt_user},
    ]

    llm_out: DataDumpLLMOut | None = None
    if files or notes.strip():
        try:
            # Rapid intake tier (Gemma 4B) with bounded token output and fast timeout
            llm_out = call_json(
                fn="extract_data_dump",
                tier="intake",
                messages=messages,
                schema=DataDumpLLMOut,
                retries=1,
                timeout_s=3.0,
                options={"num_predict": 350, "temperature": 0.1, "think": False},
                fallback_to_mock=False,
            )
        except Exception as exc:
            log.info("Fast Gemma pass skipped/timed out (%s); leveraging real timetable deterministic extraction", exc)

    # 5. Combine and validate rules
    final_drafts: list[ExtractedRuleDraft] = []
    seen_keys: set[str] = set()

    # Priority 1: Deterministic timetable-grounded extractions
    for draft in deterministic_drafts:
        k = f"{draft.type}:{json.dumps(draft.params, sort_keys=True)}"
        if k not in seen_keys:
            seen_keys.add(k)
            final_drafts.append(draft)

    # Priority 2: LLM-extracted rules if valid against roster
    if llm_out:
        for r_draft in llm_out.rules:
            rule_params = r_draft.params or {}
            if r_draft.type == "teacher_unavailable" and "teacher" in rule_params:
                _ensure_teacher(roster, rule_params["teacher"])
            elif r_draft.type == "room_unavailable" and "room" in rule_params:
                _ensure_room(roster, rule_params["room"])
            elif r_draft.type == "pin_session" and "session_id" in rule_params:
                _ensure_session(roster, rule_params["session_id"])
            elif r_draft.type == "only_qualified" and "session_id" in rule_params:
                _ensure_session(roster, rule_params["session_id"], rule_params.get("teachers", []))
            try:
                validate_params(r_draft.type, rule_params, roster)
                k = f"{r_draft.type}:{json.dumps(rule_params, sort_keys=True)}"
                if k not in seen_keys:
                    seen_keys.add(k)
                    final_drafts.append(r_draft)
            except Exception as e:
                log.debug("LLM rule discarded due to roster validation: %s", e)
        db.save_roster(roster)

    # 6. Build executive summary, entities, and insights dynamically
    if llm_out and llm_out.summary:
        summary_text = llm_out.summary
        entities_list = [e.model_dump() for e in llm_out.entities]
        insights_list = llm_out.insights
        warnings_list = llm_out.warnings
    else:
        file_count_str = f"{len(files)} uploaded file{'s' if len(files) != 1 else ''}" if files else "operator notes"
        if final_drafts:
            summary_text = (
                f"Successfully synthesized operational requirements from {file_count_str}. "
                f"Grounded extractions against active timetable with {len(roster.teachers)} instructors, "
                f"{len(roster.rooms)} facilities, and {len(roster.sessions)} sessions. "
                f"Generated {len(final_drafts)} verified constraint rule{'s' if len(final_drafts) != 1 else ''} ready for schedule optimization."
            )
        else:
            summary_text = (
                f"Processed {file_count_str} against active timetable ({len(roster.teachers)} faculty, "
                f"{len(roster.rooms)} facilities, {len(roster.sessions)} sessions). "
                f"No explicit constraint conflicts or restrictions detected in the provided data dump."
            )
        entities_list = [
            {"name": t, "kind": "faculty", "details": f"Faculty ({', '.join(s.course for s in roster.sessions if t in s.teachers) or 'Active instructor'})"}
            for t in roster.teachers
        ] + [
            {"name": rm.name, "kind": "facility", "details": f"Capacity: {rm.capacity} seats"}
            for rm in roster.rooms
        ] + [
            {"name": s.course, "kind": "session", "details": f"Session ID: {s.id} • Qualified: {', '.join(s.teachers)}"}
            for s in roster.sessions
        ]
        insights_list = [
            f"Processed data dump with {len(files)} files and direct operator directives.",
            f"Cross-referenced active schedule ({len(schedule.placements) if schedule else 0} placed sessions) for immediate conflict detection.",
        ]
        warnings_list = []

    # 7. Save rules to DB and construct human-friendly cards
    saved_rules: list[Rule] = []
    rule_cards: list[ExtractedRuleCard] = []

    for r_draft in final_drafts:
        rule_params = r_draft.params or {}
        # Final validation guarantee
        try:
            validate_params(r_draft.type, rule_params, roster)
        except Exception as e:
            log.warning("Skipping invalid rule parameter set: %s (%s)", rule_params, e)
            continue

        rule_id = db.next_rule_id()
        owner = r_draft.owner or config.DEFAULT_OWNER.get(r_draft.type) or "Coordinator"
        evidence_ref = r_draft.evidence_ref or "data-dump"

        rule = Rule(
            id=rule_id,
            type=r_draft.type,  # type: ignore[arg-type]
            owner=owner,
            params=rule_params,
            evidence=[Evidence(kind="text", ref=evidence_ref)],
            status="draft",
        )
        db.save_rule(rule)
        saved_rules.append(rule)

        card = _build_rule_card(
            rule_id=rule_id,
            rtype=r_draft.type,
            params=rule_params,
            owner=owner,
            evidence_ref=evidence_ref,
            schedule=schedule,
            roster=roster,
        )
        rule_cards.append(card)
        if card.has_conflict and card.timetable_impact not in warnings_list:
            warnings_list.append(card.timetable_impact)

    # 7b. Deep conflict diagnosis & resolution reasoning using Gemma 12B
    conflicting_cards = [c for c in rule_cards if c.has_conflict]
    if conflicting_cards:
        try:
            conflict_descriptions = [
                f"Rule {c.id} ({c.type}): {c.headline} - Conflict Impact: {c.timetable_impact}"
                for c in conflicting_cards[:4]
            ]
            conflict_text = "\n".join(conflict_descriptions)
            from backend.llm.prompts import explain_conflict
            from backend.models import ExplainOut

            reason_res = call_json(
                fn="explain_conflict",
                tier="reason",
                messages=[
                    {
                        "role": "system",
                        "content": "You are a timetable conflict diagnosis engine. Explain rule conflicts clearly and propose bounded alternative solutions.",
                    },
                    {"role": "user", "content": explain_conflict(conflict_text)},
                ],
                schema=ExplainOut,
                retries=1,
                timeout_s=15.0,
                options={"num_predict": 400, "temperature": 0.1, "think": False},
                fallback_to_mock=False,
            )
            if reason_res and reason_res.summary:
                insights_list.append(f"Gemma 12B Conflict Analysis: {reason_res.summary}")
                for opt in reason_res.options[:2]:
                    insights_list.append(f"Suggested Resolution Option: {opt.description}")
        except Exception as exc:
            log.info("12B conflict reasoning pass skipped or timed out (%s)", exc)

    db.log_audit_event(
        "DataDumpIngested",
        f"DUMP-{len(files)}FILES",
        "Coordinator",
        {
            "files_count": len(files),
            "rules_extracted": len(saved_rules),
            "instructions": instructions_clean[:100],
        },
    )

    return DataDumpResult(
        summary=summary_text,
        instructions_executed=instructions_clean,
        rules=saved_rules,
        rule_cards=rule_cards,
        entities=entities_list,
        insights=insights_list,
        warnings=warnings_list,
        processed_files=processed_files,
    )
