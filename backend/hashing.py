"""Deterministic canonical hashing for schedules, rules, and audit verification."""
from __future__ import annotations

import hashlib
import json
import os
from backend.models import Schedule


def canonical(obj: object) -> str:
    """Format JSON deterministically with sorted keys and compact separators."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def schedule_obj(schedule: Schedule) -> dict:
    """Convert schedule to canonical dict sorted by session ID."""
    return {
        "version": schedule.version,
        "placements": sorted(
            (p.model_dump() for p in schedule.placements),
            key=lambda p: p["session_id"],
        ),
    }


def _hash(data: bytes) -> bytes:
    """Compute standard SHA-256 cryptographic digest."""
    return hashlib.sha256(data).digest()


def schedule_hash(schedule: Schedule) -> bytes:
    """Compute canonical 32-byte digest of a schedule."""
    return _hash(canonical(schedule_obj(schedule)).encode("utf-8"))


def new_salt() -> bytes:
    """Generate 16 cryptographically random salt bytes."""
    return os.urandom(16)


def rule_hash(rule_id: str, rtype: str, owner: str, salt: bytes) -> bytes:
    """Compute salted canonical digest for a confirmed rule."""
    payload = {"id": rule_id, "type": rtype, "owner": owner}
    return _hash(salt + canonical(payload).encode("utf-8"))


def option_hash(rule_id: str, new_params: dict) -> bytes:
    """Compute canonical digest for a proposed relaxation option."""
    payload = {"rule_id": rule_id, "new_params": new_params}
    return _hash(canonical(payload).encode("utf-8"))


def hexs(value: bytes) -> str:
    """Format bytes as 0x-prefixed hexadecimal string."""
    return "0x" + value.hex()
