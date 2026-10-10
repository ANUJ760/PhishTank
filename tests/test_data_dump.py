"""Tests for unified multi-modal data dump intake."""
from __future__ import annotations

from pathlib import Path
import pytest
from backend import api
from backend.intake.data_dump import ingest_data_dump
from backend.registry import db


def test_ingest_data_dump_basic():
    api.reset_demo()
    api.seed_demo()

    files = [
        ("roster_sample.csv", b"teacher,course,day,slot\nProf. Rao,DB_LAB,0,0\nProf. Mehta,ALGO,1,1"),
        ("memo.txt", b"Prof. Rao cannot teach on Monday morning between 09:00 and 12:00 due to department duties."),
    ]
    instructions = "Extract professor availability constraints and lab qualifications."
    notes = "Direct phone call: Make sure DB_LAB is only handled by Prof. Rao."

    result = ingest_data_dump(files=files, instructions=instructions, notes=notes)

    assert result.summary
    assert len(result.processed_files) == 2
    assert result.instructions_executed == instructions
    assert len(result.rules) > 0
    assert len(result.entities) > 0


def test_ingest_data_dump_excel_workload():
    """Verify real tabular extraction from an Excel sheet without dummy fallback."""
    api.reset_demo()
    api.seed_demo()

    workload_path = Path("samples/workload.xlsx")
    assert workload_path.exists()
    content = workload_path.read_bytes()

    result = ingest_data_dump(
        files=[("workload.xlsx", content)],
        instructions="Extract all session qualification requirements from the spreadsheet.",
        notes="",
    )

    assert len(result.rules) >= 4
    # Real course sessions from workload.xlsx
    session_ids = [r.params.get("session_id") for r in result.rules if r.type == "only_qualified"]
    assert "DB_LAB" in session_ids or "DATABASE_LAB" in session_ids
    assert "OS_LEC" in session_ids or "OPERATING_SYSTEMS" in session_ids


def test_ingest_data_dump_arbitrary_entities():
    """Verify that arbitrary faculty and rooms are parsed from files, registered, and validated."""
    api.reset_demo()
    api.seed_demo()

    csv_content = (
        "Faculty,Day,Slot,Status\n"
        "Dr. Alan Turing,Monday,0,Unavailable for research\n"
        "Dr. Marie Curie,Wednesday,3,Conference travel\n"
    ).encode("utf-8")

    memo_content = (
        "Facility Notice: Room-505 is closed for renovation on Thursday afternoon. "
        "Quantum Physics session must only be handled by Dr. Alan Turing."
    ).encode("utf-8")

    result = ingest_data_dump(
        files=[("availability.csv", csv_content), ("memo.txt", memo_content)],
        instructions="Extract real faculty leaves, facility closures, and qualifications.",
        notes="",
    )

    # Verify real extracted entities
    rule_teachers = [r.params.get("teacher") for r in result.rules if r.type == "teacher_unavailable"]
    assert "Dr. Alan Turing" in rule_teachers
    assert "Dr. Marie Curie" in rule_teachers

    # Verify real room extracted
    rule_rooms = [r.params.get("room") for r in result.rules if r.type == "room_unavailable"]
    assert any("505" in rm for rm in rule_rooms)

    # Verify registered in db roster
    current_roster = db.get_roster()
    assert "Dr. Alan Turing" in current_roster.teachers
    assert "Dr. Marie Curie" in current_roster.teachers
    assert any("505" in rm.name for rm in current_roster.rooms)

    # Verify cards are human readable
    assert len(result.rule_cards) > 0
    card_headlines = [c.headline for c in result.rule_cards]
    assert any("Dr. Alan Turing" in h for h in card_headlines)


def test_ingest_data_dump_no_dummy_fallback():
    """Verify that an empty dump does NOT invent fake 'Prof. Rao' rules."""
    api.reset_demo()
    api.seed_demo()

    result = ingest_data_dump(
        files=[],
        instructions="Extract any constraints present.",
        notes="",
    )

    # Zero input should produce zero fake rules
    assert len(result.rules) == 0
    assert len(result.rule_cards) == 0
    assert "No explicit constraint conflicts" in result.summary
