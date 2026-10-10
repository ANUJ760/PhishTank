"""Strict API and persistence schemas."""
from __future__ import annotations
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field
from backend import config

class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")

RuleType = Literal["teacher_unavailable", "room_unavailable", "pin_session", "only_qualified"]
class Evidence(Strict):
    kind: Literal["audio", "image", "sheet", "text"]
    ref: str = Field(min_length=1)
class Rule(Strict):
    id: str
    type: RuleType
    owner: str
    params: dict
    evidence: list[Evidence] = Field(default_factory=list)
    status: Literal["draft", "confirmed", "rejected"] = "draft"
class Room(Strict):
    name: str
    capacity: int = Field(ge=0)
class Session(Strict):
    id: str
    course: str
    teachers: list[str]
    size: int = Field(default=30, ge=0)
class Roster(Strict):
    teachers: list[str]
    rooms: list[Room]
    sessions: list[Session]
class Placement(Strict):
    session_id: str
    teacher: str
    room: str
    day: int
    slot: int
class Schedule(Strict):
    placements: list[Placement]
    version: int = Field(default=1, ge=1)
class Conflict(Strict):
    rule_ids: list[str]
    owners: list[str]
class RelaxOption(Strict):
    id: str
    rule_id: str
    new_params: dict
    description: str
    approver: str
    verified: bool = False
    option_hash: str = ""
    approved: bool = False
    approved_by: str | None = None
class Explanation(Strict):
    summary: str
    options: list[RelaxOption]
class DraftRule(Strict):
    type: RuleType
    params: dict
    evidence_ref: str = ""
class DraftRulesOut(Strict):
    rules: list[DraftRule]
class ParserOut(Strict):
    code: str
class ExplainOptionOut(Strict):
    rule_id: str
    new_params: dict
    description: str
class ExplainOut(Strict):
    summary: str
    options: list[ExplainOptionOut]

def validate_params(rtype: str, p: dict, roster: Roster) -> None:
    if not isinstance(p, dict):
        raise ValueError("rule params must be an object")
    teachers, rooms = set(roster.teachers), {r.name for r in roster.rooms}
    sessions = {s.id for s in roster.sessions}
    if rtype in {"teacher_unavailable", "room_unavailable", "pin_session"}:
        keys = {"teacher": {"teacher", "day", "slots"}, "room_unavailable": {"room", "day", "slots"}, "pin_session": {"session_id", "day", "slots"}}
        # The first dict key is the actual type; spelling kept explicit for strict shape checks.
        if set(p) != keys.get(rtype, {"teacher", "day", "slots"}):
            raise ValueError(f"{rtype} params have incorrect keys")
        entity = p.get("teacher") if rtype == "teacher_unavailable" else p.get("room") if rtype == "room_unavailable" else p.get("session_id")
        known = teachers if rtype == "teacher_unavailable" else rooms if rtype == "room_unavailable" else sessions
        if entity not in known:
            raise ValueError(f"unknown {rtype} entity")
        day, slots = p.get("day"), p.get("slots")
        if type(day) is not int or not 0 <= day < config.DAYS:
            raise ValueError("bad day")
        if not isinstance(slots, list) or not slots or any(type(t) is not int or not 0 <= t < config.SLOTS_PER_DAY for t in slots):
            raise ValueError("bad slots")
        if len(slots) != len(set(slots)):
            raise ValueError("slots must be unique")
    elif rtype == "only_qualified":
        if set(p) != {"session_id", "teachers"} or p["session_id"] not in sessions:
            raise ValueError("only_qualified params have incorrect keys or session")
        if not isinstance(p["teachers"], list) or not p["teachers"] or any(t not in teachers for t in p["teachers"]):
            raise ValueError("unknown teacher")
        session = next(s for s in roster.sessions if s.id == p["session_id"])
        if any(t not in session.teachers for t in p["teachers"]):
            raise ValueError("teacher is not a candidate for this session")
    else:
        raise ValueError("unknown rule type")
