"""Tests for unified multi-modal data dump intake."""
from __future__ import annotations

import pytest
from backend import api
from backend.intake.data_dump import ingest_data_dump


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
