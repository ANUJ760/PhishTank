"""Comprehensive test suite for PNG image and voice audio multimodal intake."""
from __future__ import annotations

import io
from pathlib import Path
from PIL import Image
import pytest
from starlette.testclient import TestClient

from backend import api
from backend.intake.data_dump import ingest_data_dump
from backend.registry import db


@pytest.fixture(autouse=True)
def reset_db_state():
    """Reset and seed baseline DB before each test."""
    api.reset_demo()
    api.seed_demo()


@pytest.fixture
def client():
    """Test client for FastAPI / Starlette endpoints."""
    from backend.server import app
    return TestClient(app)


def _create_minimal_png() -> bytes:
    """Generate in-memory valid PNG image bytes."""
    buf = io.BytesIO()
    img = Image.new("RGB", (640, 480), color=(30, 41, 59))
    img.save(buf, format="PNG")
    return buf.getvalue()


def _get_test_data_file(rel_path: str) -> bytes:
    """Load test asset from test_data directory or create fallback."""
    full_path = Path("test_data") / rel_path
    if full_path.exists():
        return full_path.read_bytes()
    if rel_path.endswith(".png"):
        return _create_minimal_png()
    raise FileNotFoundError(f"Test data asset not found: {full_path}")


# =========================================================================
# 1. Direct API Functions for PNG Image & Voice Audio
# =========================================================================
def test_ingest_image_direct():
    """Verify api.ingest_image extracts valid Rule items with image evidence."""
    png_bytes = _create_minimal_png()
    rules = api.ingest_image(png_bytes, "schedule_whiteboard.png")
    assert isinstance(rules, list)
    assert len(rules) >= 1
    for r in rules:
        assert r.type in {"teacher_unavailable", "room_unavailable", "pin_session", "only_qualified"}
        assert len(r.evidence) >= 1
        assert r.evidence[0].kind == "image"
        assert "schedule_whiteboard.png" in r.evidence[0].ref
        assert r.owner != ""


def test_ingest_audio_direct():
    """Verify api.ingest_audio extracts valid Rule items with audio evidence."""
    wav_path = Path("test_data/01_university_academic/dean_voice_memo.wav")
    assert wav_path.exists(), "Synthesized WAV file must exist in test_data"
    wav_bytes = wav_path.read_bytes()

    rules = api.ingest_audio(wav_bytes, "dean_voice_memo.wav")
    assert isinstance(rules, list)
    assert len(rules) >= 1
    for r in rules:
        assert r.type in {"teacher_unavailable", "room_unavailable", "pin_session", "only_qualified"}
        assert len(r.evidence) >= 1
        assert r.evidence[0].kind == "audio"
        assert "dean_voice_memo.wav" in r.evidence[0].ref
        assert r.owner != ""


# =========================================================================
# 2. Data Dump Unified Intake with PNG Images
# =========================================================================
def test_ingest_data_dump_with_png():
    """Verify ingest_data_dump accepts PNG images and produces human-readable cards."""
    png_path = Path("test_data/01_university_academic/whiteboard_weekly_schedule.png")
    png_bytes = png_path.read_bytes() if png_path.exists() else _create_minimal_png()

    result = ingest_data_dump(
        files=[("whiteboard_weekly_schedule.png", png_bytes)],
        instructions="Extract scheduled course pins and laboratory maintenance from the whiteboard image.",
        notes="",
    )

    # 1. File summary check
    assert len(result.processed_files) == 1
    file_summary = result.processed_files[0]
    assert file_summary.filename == "whiteboard_weekly_schedule.png"
    assert file_summary.file_type == "image"
    assert "Visual schedule/board image" in file_summary.preview or "Visual asset" in file_summary.preview
    assert file_summary.status == "processed"

    # 2. Rules and rule cards
    assert len(result.rules) >= 1
    assert len(result.rule_cards) == len(result.rules)

    for card in result.rule_cards:
        assert card.headline != ""
        assert card.plain_description != ""
        assert not card.plain_description.startswith("{")
        assert "whiteboard_weekly_schedule.png" in card.evidence_ref

    # 3. Processing stages record
    stages = [p.get("stage") for p in result.processing]
    assert any("Visual intake" in s for s in stages)


# =========================================================================
# 3. Data Dump Unified Intake with Voice Audio (WAV)
# =========================================================================
def test_ingest_data_dump_with_voice_audio():
    """Verify ingest_data_dump accepts WAV audio memos and produces cards."""
    wav_path = Path("test_data/01_university_academic/dean_voice_memo.wav")
    assert wav_path.exists()
    wav_bytes = wav_path.read_bytes()

    result = ingest_data_dump(
        files=[("dean_voice_memo.wav", wav_bytes)],
        instructions="Extract oral unavailability directives from the Dean's voice message.",
        notes="",
    )

    # 1. File summary check
    assert len(result.processed_files) == 1
    file_summary = result.processed_files[0]
    assert file_summary.filename == "dean_voice_memo.wav"
    assert file_summary.file_type == "audio"
    assert "Voice memo" in file_summary.preview or "Audio memo" in file_summary.preview

    # 2. Rules and cards
    assert len(result.rules) >= 1
    assert len(result.rule_cards) == len(result.rules)
    for card in result.rule_cards:
        assert card.headline != ""
        assert "dean_voice_memo.wav" in card.evidence_ref

    # 3. Processing stages record
    stages = [p.get("stage") for p in result.processing]
    assert any("Voice intake" in s for s in stages)


# =========================================================================
# 4. Multimodal Fusion: Tabular + PNG Image + WAV Audio + Notes
# =========================================================================
def test_ingest_data_dump_multimodal_all_combined():
    """Verify heterogeneous dump with Excel/CSV + PNG whiteboard + WAV memo + notes."""
    csv_bytes = b"Faculty,Course,Day,Slot\nProf. Alice Vance,CS501,0,0\nProf. Bob Chen,CS502,1,1\n"
    png_bytes = _create_minimal_png()
    wav_path = Path("test_data/01_university_academic/dean_voice_memo.wav")
    wav_bytes = wav_path.read_bytes()

    files = [
        ("faculty_manifest.csv", csv_bytes),
        ("weekly_whiteboard.png", png_bytes),
        ("dean_dispatch.wav", wav_bytes),
    ]

    result = ingest_data_dump(
        files=files,
        instructions="Consolidate all timetable requirements across visual whiteboard, audio dispatch, and manifest.",
        notes="Administrative Note: Prof. Alice Vance cannot take slots on Thursday afternoon.",
    )

    # All 3 files processed without errors
    assert len(result.processed_files) == 3
    file_types = {f.file_type for f in result.processed_files}
    assert "csv" in file_types
    assert "image" in file_types
    assert "audio" in file_types

    # Multiple rules extracted
    assert len(result.rules) >= 3
    assert len(result.rule_cards) == len(result.rules)

    # Evidence references should span different media
    evidence_refs = [c.evidence_ref for c in result.rule_cards]
    assert any("png" in ref.lower() for ref in evidence_refs)
    assert any("wav" in ref.lower() for ref in evidence_refs)


# =========================================================================
# 5. HTTP Endpoints for Image and Audio Intake
# =========================================================================
def test_http_intake_image_endpoint(client: TestClient):
    """Verify POST /api/v1/intake/image returns 200 and structured rules."""
    png_bytes = _create_minimal_png()
    res = client.post(
        "/api/v1/intake/image",
        files={"file": ("timetable_snap.png", png_bytes, "image/png")},
    )
    assert res.status_code == 200
    data = res.json()
    assert isinstance(data, list)
    assert len(data) >= 1
    assert "params" in data[0]
    assert "type" in data[0]


def test_http_intake_audio_endpoint(client: TestClient):
    """Verify POST /api/v1/intake/audio returns 200 and structured rules."""
    wav_path = Path("test_data/01_university_academic/dean_voice_memo.wav")
    wav_bytes = wav_path.read_bytes()
    res = client.post(
        "/api/v1/intake/audio",
        files={"file": ("memo.wav", wav_bytes, "audio/wav")},
    )
    assert res.status_code == 200
    data = res.json()
    assert isinstance(data, list)
    assert len(data) >= 1
    assert "params" in data[0]
    assert "type" in data[0]


def test_http_intake_dump_endpoint_multimodal(client: TestClient):
    """Verify POST /api/v1/intake/dump handles multimodal uploads cleanly."""
    png_bytes = _create_minimal_png()
    wav_path = Path("test_data/01_university_academic/dean_voice_memo.wav")
    wav_bytes = wav_path.read_bytes()

    res = client.post(
        "/api/v1/intake/dump",
        files=[
            ("files", ("whiteboard.png", png_bytes, "image/png")),
            ("files", ("directive.wav", wav_bytes, "audio/wav")),
        ],
        data={
            "instructions": "Synthesize whiteboard image and audio memo.",
            "notes": "Emergency schedule review requested.",
        },
    )
    assert res.status_code == 200
    data = res.json()
    assert "summary" in data
    assert "rule_cards" in data
    assert len(data["rule_cards"]) >= 2
    assert "processed_files" in data
    assert len(data["processed_files"]) == 2


# =========================================================================
# 6. Rejection of Unsupported Arbitrary Binary
# =========================================================================
def test_unsupported_binary_rejected():
    """Verify arbitrary unknown binary format raises clear error."""
    with pytest.raises(ValueError, match="Cannot read timetable data"):
        ingest_data_dump(
            files=[("corrupted_archive.bin", b"\x00\x01\x02\x03\x04\x05")],
            instructions="",
            notes="",
        )
