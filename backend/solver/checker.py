"""Independent schedule validator. This module deliberately does not import OR-Tools."""
from collections import Counter
from backend import config
from backend.models import Rule, Roster, Schedule

def check(schedule: Schedule, roster: Roster, rules: list[Rule]) -> list[str]:
    violations=[]; sessions={s.id:s for s in roster.sessions}; rooms={r.name:r for r in roster.rooms}
    counts=Counter(p.session_id for p in schedule.placements)
    for sid in sessions:
        if counts[sid]!=1: violations.append(f"Session {sid} is placed {counts[sid]} times (must be 1)")
    for p in schedule.placements:
        session=sessions.get(p.session_id)
        if session is None: violations.append(f"Unknown session {p.session_id}"); continue
        if p.teacher not in session.teachers: violations.append(f"{p.teacher} cannot teach {p.session_id}")
        room=rooms.get(p.room)
        if room is None: violations.append(f"Unknown room {p.room}")
        elif room.capacity<session.size: violations.append(f"Room {p.room} too small for {p.session_id}")
        if not 0<=p.day<config.DAYS or not 0<=p.slot<config.SLOTS_PER_DAY:
            violations.append(f"{p.session_id} outside the week grid")
    for field,label in (("room","Room"),("teacher","Teacher")):
        counts=Counter((getattr(p,field),p.day,p.slot) for p in schedule.placements if 0<=p.day<config.DAYS and 0<=p.slot<config.SLOTS_PER_DAY)
        for (who,day,slot),n in counts.items():
            if n>1: violations.append(f"{label} clash: {who} has {n} sessions on {config.DAY_NAMES[day]} slot {slot}")
    for rule in rules:
        if rule.status!="confirmed": continue
        q=rule.params
        for p in schedule.placements:
            if rule.type=="teacher_unavailable" and p.teacher==q["teacher"] and p.day==q["day"] and p.slot in q["slots"]: violations.append(f"{rule.id}: {p.teacher} teaches {p.session_id} while unavailable")
            elif rule.type=="room_unavailable" and p.room==q["room"] and p.day==q["day"] and p.slot in q["slots"]: violations.append(f"{rule.id}: room {p.room} used while closed")
            elif rule.type=="pin_session" and p.session_id==q["session_id"] and not(p.day==q["day"] and p.slot in q["slots"]): violations.append(f"{rule.id}: {p.session_id} is not in its pinned slot")
            elif rule.type=="only_qualified" and p.session_id==q["session_id"] and p.teacher not in q["teachers"]: violations.append(f"{rule.id}: {p.teacher} is not qualified for {p.session_id}")
    return violations
