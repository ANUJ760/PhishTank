"""Comprehensive tests for layout-aware parser synthesis, caching, dynamic roster expansion, and 12B/4B sync."""
from __future__ import annotations
import csv
import io
from pathlib import Path
import pytest
from backend import api, config
from backend.intake import sheet_parser, sandbox
from backend.models import Roster, Session, Room
from backend.registry import db


def test_sheet_parser_dynamic_roster_expansion(tmp_path: Path):
    """Spreadsheet with new courses and previously unregistered faculty expands the roster."""
    api.reset_demo()
    api.seed_demo()
    roster_before = db.get_roster()
    assert "Dr. Richard Feynman" not in roster_before.teachers
    assert not any(s.course == "Quantum Electrodynamics" for s in roster_before.sessions)

    # Create CSV spreadsheet
    csv_file = tmp_path / "quantum_workload.csv"
    with csv_file.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Course", "Qualified Faculty", "Hours"])
        writer.writerow(["Quantum Electrodynamics", "Dr. Richard Feynman, Prof. Rao", "4"])
        writer.writerow(["Database Lab", "Prof. Rao, Dr. Ada Lovelace", "3"])

    res = sheet_parser.ingest_sheet(csv_file, "quantum_workload.csv")
    assert len(res.rules) == 2
    assert res.cache_hit is False

    # Check that teachers and sessions were dynamically registered into database
    roster_after = db.get_roster()
    assert "Dr. Richard Feynman" in roster_after.teachers
    assert "Dr. Ada Lovelace" in roster_after.teachers
    assert any("Quantum" in s.course for s in roster_after.sessions)

    # Verify second ingestion of same layout hits cache
    res2 = sheet_parser.ingest_sheet(csv_file, "quantum_workload.csv")
    assert res2.cache_hit is True
    assert res2.tokens_used == 0


def test_sheet_parser_fallback_parser():
    """Verify default fallback parser code runs properly in sandbox and produces valid output."""
    sample_file = Path("samples/workload.xlsx")
    assert sample_file.exists()

    code = sheet_parser._default_parser_code()
    rows = sandbox.run_parser(code, sample_file)
    assert len(rows) == 6
    assert rows[0]["course"] == "Database Lab"
    assert rows[0]["teachers"] == ["Prof. Rao"]
    assert rows[0]["source_cell"] == "B2"


def test_sheet_parser_layout_signatures(tmp_path: Path):
    """Layout signature matches identically for sheets with the same header schema."""
    csv1 = tmp_path / "s1.csv"
    csv1.write_text("Course,Faculty\nMath,Smith\n", encoding="utf-8")
    csv2 = tmp_path / "s2.csv"
    csv2.write_text("Course,Faculty\nPhysics,Dirac\n", encoding="utf-8")
    csv3 = tmp_path / "s3.csv"
    csv3.write_text("Subject,Instructor,Credits\nChemistry,Curie,4\n", encoding="utf-8")

    sig1 = sheet_parser.layout_signature(csv1)
    sig2 = sheet_parser.layout_signature(csv2)
    sig3 = sheet_parser.layout_signature(csv3)

    assert sig1 == sig2
    assert sig1 != sig3


def test_data_dump_with_conflicts_triggers_12b_reasoning():
    """When a dumped rule directly clashes with the schedule, 12B conflict analysis is activated."""
    api.reset_demo()
    api.seed_demo()
    sched = db.latest_schedule()
    assert sched is not None

    # Pick first placement to construct a clash
    p0 = sched.placements[0]
    assigned_teacher = p0.teacher
    day_name = {0: "Monday", 1: "Tuesday", 2: "Wednesday", 3: "Thursday", 4: "Friday"}.get(p0.day, "Monday")
    slot_num = p0.slot

    memo = f"URGENT: {assigned_teacher} is on medical emergency leave on {day_name} at Slot {slot_num}."

    result = api.ingest_dump(
        files=[("urgent_leave.txt", memo.encode("utf-8"))],
        instructions="Flag urgent teacher leave and assess timetable clashes.",
        notes="",
    )

    # Rule cards should detect conflict
    conflicted_cards = [c for c in result.rule_cards if c.has_conflict]
    assert len(conflicted_cards) > 0
    assert any("clash" in c.timetable_impact.lower() or "conflict" in c.timetable_impact.lower() for c in conflicted_cards)

    # Check that warnings list contains the conflict impact
    assert len(result.warnings) > 0


def test_generated_parser_cannot_register_names_absent_from_upload(monkeypatch):
    from backend.intake import sheet_parser
    from backend.models import Roster
    roster = Roster(teachers=[], rooms=[], sessions=[])
    monkeypatch.setattr(sheet_parser.db, 'save_roster', lambda *args: None)
    good, failed = sheet_parser._validated([
        {'course': 'Applied Optics', 'teachers': ['Prof. Rao'], 'source_cell': 'B2'},
    ], roster, {'applied optics', 'dr. lina rivera'})
    assert not good
    assert failed == 1
    assert roster.teachers == []
    assert roster.sessions == []
