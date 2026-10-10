"""Tamper-proof cryptographic audit ledger architecture.

Maintains an immutable, append-only hash-chained event log ensuring data integrity,
non-repudiation, and auditability without relying on external blockchains or web3.
"""
from __future__ import annotations

import hashlib
import json
import logging
import time
from typing import Any
from pydantic import BaseModel, Field

from backend.registry import db

log = logging.getLogger(__name__)

GENESIS_HASH = "0" * 64


class LedgerEntry(BaseModel):
    """Immutable entry in the tamper-proof cryptographic ledger."""
    seq: int
    entry_id: str
    event: str
    entity_id: str
    actor: str
    details: dict[str, Any] = Field(default_factory=dict)
    prev_hash: str = GENESIS_HASH
    entry_hash: str
    timestamp: float = Field(default_factory=time.time)

    # Backwards-compatible fields for UI clients
    @property
    def block(self) -> int:
        return self.seq

    @property
    def idx(self) -> int:
        return 0

    @property
    def args(self) -> dict[str, Any]:
        return self.details


def canonical_json(data: Any) -> str:
    """Deterministically serialize data to JSON with sorted keys."""
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def compute_entry_hash(
    seq: int,
    event: str,
    entity_id: str,
    actor: str,
    details: dict[str, Any],
    prev_hash: str,
    timestamp: float,
) -> str:
    """Compute deterministic SHA-256 hash chaining this entry to the ledger."""
    payload = canonical_json(details or {})
    # Fixed precision timestamp to prevent float string formatting divergence
    ts_str = f"{timestamp:.4f}"
    content = f"{seq}|{event}|{entity_id}|{actor}|{payload}|{prev_hash}|{ts_str}"
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


class TamperProofLedger:
    """Manages appending, querying, and cryptographically validating ledger entries."""

    @staticmethod
    def append(
        event: str,
        entity_id: str,
        actor: str = "System",
        details: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Record an event with cryptographic SHA-256 hash chaining."""
        details = details or {}
        now = time.time()

        # Fetch the latest entry to link the hash chain
        latest = db.get_latest_audit_entry()
        if latest and latest.get("seq") is not None:
            seq = int(latest["seq"]) + 1
            prev_hash = latest["entry_hash"] or GENESIS_HASH
        else:
            seq = 1
            prev_hash = GENESIS_HASH

        entry_hash = compute_entry_hash(seq, event, entity_id, actor, details, prev_hash, now)

        entry_data = {
            "seq": seq,
            "entry_id": f"LE-{seq:06d}",
            "event": event,
            "entity_id": entity_id,
            "actor": actor,
            "details": details,
            "prev_hash": prev_hash,
            "entry_hash": entry_hash,
            "timestamp": now,
            # Backwards compatibility properties
            "block": seq,
            "idx": 0,
            "args": details,
        }

        db.insert_ledger_entry(
            seq=seq,
            event=event,
            entity_id=entity_id,
            user_id=actor,
            details=details,
            prev_hash=prev_hash,
            entry_hash=entry_hash,
            created_at=now,
        )

        log.info("Ledger entry appended: seq=%d event=%s hash=%s", seq, event, entry_hash[:16])
        return entry_data

    @staticmethod
    def get_entries(event_filter: str | None = None, limit: int = 200) -> list[dict[str, Any]]:
        """Retrieve recent ledger entries with full cryptographic provenance."""
        raw_rows = db.list_audit_events_extended(event_filter=event_filter, limit=limit)
        return raw_rows

    @staticmethod
    def verify_integrity() -> dict[str, Any]:
        """Verify unbroken SHA-256 chain and data integrity of all ledger entries.

        Detects:
        - Payload tampering (hash mismatch)
        - Reordering or insertion attacks (prev_hash mismatch)
        - Deletion of intermediate records
        """
        all_entries = db.list_all_ledger_entries()
        # Verify entries that are part of the cryptographic hash chain
        chained_entries = [e for e in all_entries if e.get("entry_hash")]
        total = len(chained_entries)

        if total == 0:
            return {
                "verified": True,
                "valid": True,
                "total_entries": 0,
                "tip_hash": GENESIS_HASH,
                "genesis_hash": GENESIS_HASH,
                "message": "Ledger is empty; genesis state valid.",
            }

        expected_prev = chained_entries[0]["prev_hash"]

        for i, entry in enumerate(chained_entries):
            seq = entry["seq"]

            # 1. Verify link to previous entry (for all entries after the first)
            if i > 0 and entry["prev_hash"] != expected_prev:
                return {
                    "verified": False,
                    "valid": False,
                    "total_entries": total,
                    "tampered_seq": seq,
                    "tip_hash": entry["entry_hash"],
                    "error": (
                        f"Broken chain link at seq {seq}: "
                        f"expected prev_hash {expected_prev[:16]}..., "
                        f"got {entry['prev_hash'][:16]}..."
                    ),
                    "message": f"Tampering detected: Broken chain link at seq {seq}",
                }

            # 2. Recompute and verify entry hash against payload
            recomputed = compute_entry_hash(
                seq=seq,
                event=entry["event"],
                entity_id=entry["entity_id"],
                actor=entry["actor"],
                details=entry["details"],
                prev_hash=entry["prev_hash"],
                timestamp=entry["timestamp"],
            )

            if entry["entry_hash"] != recomputed:
                return {
                    "verified": False,
                    "valid": False,
                    "total_entries": total,
                    "tampered_seq": seq,
                    "tip_hash": entry["entry_hash"],
                    "error": (
                        f"Tampered record payload at seq {seq}: "
                        f"recorded hash {entry['entry_hash'][:16]}... != "
                        f"recomputed hash {recomputed[:16]}..."
                    ),
                    "message": f"Tampering detected: Payload hash mismatch at seq {seq}",
                }

            expected_prev = entry["entry_hash"]

        tip_hash = chained_entries[-1]["entry_hash"]
        return {
            "verified": True,
            "valid": True,
            "total_entries": total,
            "tip_hash": tip_hash,
            "genesis_hash": chained_entries[0]["entry_hash"],
            "message": f"Tamper-proof ledger verified across all {total} entries.",
        }


# Singleton instance
ledger = TamperProofLedger()
