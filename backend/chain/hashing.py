"""Canonical hashes used for local verification and ledger anchors."""
from __future__ import annotations
import json, os
from backend.models import Schedule

def canonical(obj: object) -> str:
    return json.dumps(obj,sort_keys=True,separators=(",",":"),ensure_ascii=False)
def schedule_obj(schedule: Schedule) -> dict:
    return {"version":schedule.version,"placements":sorted((p.model_dump() for p in schedule.placements),key=lambda p:p["session_id"])}
def _keccak(data: bytes) -> bytes:
    try:
        from web3 import Web3
    except ImportError as exc: raise RuntimeError("Install web3 to use cryptographic hash functions") from exc
    return bytes(Web3.keccak(data))
def schedule_hash(schedule: Schedule) -> bytes: return _keccak(canonical(schedule_obj(schedule)).encode())
def new_salt() -> bytes: return os.urandom(16)
def rule_hash(rule_id: str,rtype: str,owner: str,salt: bytes) -> bytes: return _keccak(salt+canonical({"id":rule_id,"type":rtype,"owner":owner}).encode())
def option_hash(rule_id: str,new_params: dict) -> bytes: return _keccak(canonical({"rule_id":rule_id,"new_params":new_params}).encode())
def hexs(value: bytes) -> str:
    try:
        from web3 import Web3
        return Web3.to_hex(value)
    except ImportError: return "0x"+value.hex()
