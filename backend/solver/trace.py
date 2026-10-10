"""Rule provenance lookup for a scheduled session."""
from backend.models import Rule, Schedule

def why(session_id: str, schedule: Schedule, rules: list[Rule]) -> list[Rule]:
    placement=next((p for p in schedule.placements if p.session_id==session_id),None)
    if placement is None: return []
    result=[]
    for rule in rules:
        if rule.status!="confirmed": continue
        p=rule.params
        if p.get("session_id")==session_id or p.get("teacher")==placement.teacher or p.get("room")==placement.room or (p.get("day")==placement.day and placement.slot in p.get("slots",[])):
            result.append(rule)
    return result
