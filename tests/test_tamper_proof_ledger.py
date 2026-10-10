"""Unit tests for the tamper-proof cryptographic audit ledger architecture."""
import pytest
from backend.ledger import TamperProofLedger, compute_entry_hash, GENESIS_HASH
from backend.registry import db


def test_ledger_append_and_hash_chaining():
    """Verify that ledger entries are append-only and cryptographically hash-chained."""
    db.init_db()

    # Append test events
    e1 = TamperProofLedger.append(
        event="RuleRegistered",
        entity_id="R101",
        actor="Prof. Rao",
        details={"type": "teacher_unavailable", "slots": [1, 2]},
    )
    assert e1["seq"] >= 1
    assert e1["entry_hash"] != ""
    assert len(e1["entry_hash"]) == 64

    e2 = TamperProofLedger.append(
        event="RelaxationApproved",
        entity_id="O101",
        actor="Dept Head",
        details={"approved": True, "rule_id": "R101"},
    )
    assert e2["seq"] == e1["seq"] + 1
    # Check cryptographic link
    assert e2["prev_hash"] == e1["entry_hash"]
    assert len(e2["entry_hash"]) == 64


def test_ledger_integrity_verification():
    """Verify that verify_integrity passes on valid ledger chain."""
    result = TamperProofLedger.verify_integrity()
    assert result["verified"] is True
    assert result["total_entries"] >= 2
    assert "Tamper-proof ledger verified" in result["message"]


def test_ledger_detects_payload_tampering():
    """Verify that tampering with an entry's payload is immediately flagged."""
    # Append an entry
    e = TamperProofLedger.append(
        event="SchedulePublished",
        entity_id="SCHED-01",
        actor="Coordinator",
        details={"version": 1, "hash": "0xabc123"},
    )
    tampered_seq = e["seq"]

    # Directly tamper with the database record payload
    with db._connect() as conn:
        conn.execute(
            "UPDATE audit_events SET details = %s WHERE id = %s",
            ('{"version": 999, "hash": "0xhacked"}', tampered_seq),
        )

    # Verification must fail
    res = TamperProofLedger.verify_integrity()
    assert res["verified"] is False
    assert res["tampered_seq"] == tampered_seq
    assert "Tampered record payload" in res["error"]


def test_compute_entry_hash_determinism():
    """Verify deterministic hash computation regardless of dict key ordering."""
    h1 = compute_entry_hash(
        seq=1,
        event="TestEvent",
        entity_id="E1",
        actor="Alice",
        details={"z": 1, "a": 2},
        prev_hash=GENESIS_HASH,
        timestamp=1700000000.0,
    )
    h2 = compute_entry_hash(
        seq=1,
        event="TestEvent",
        entity_id="E1",
        actor="Alice",
        details={"a": 2, "z": 1},
        prev_hash=GENESIS_HASH,
        timestamp=1700000000.0,
    )
    assert h1 == h2
    assert len(h1) == 64
