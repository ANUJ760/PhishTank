"""Independent schedule validator for GeCompose.

This validator performs mathematical and constraint verification independently of CP-SAT,
ensuring no unverified or invalid assignment can be accepted as a valid schedule.
"""

from __future__ import annotations

from typing import Sequence
from gecompose.models import ScheduledAssignment, SchedulingProblem, TimeSlot, Teacher, Room, Session


def verify_schedule(
    problem: SchedulingProblem, 
    assignments: Sequence[ScheduledAssignment]
) -> tuple[bool, list[str]]:
    """Verify that a set of session assignments completely and correctly satisfies all hard constraints.
    
    Args:
        problem: The original scheduling problem definition.
        assignments: The list of scheduled session assignments to verify.
        
    Returns:
        (is_valid, violations): A boolean indicating if all hard constraints hold,
        and a list of human-readable violation descriptions if any fail.
    """
    violations: list[str] = []

    teacher_map: dict[str, Teacher] = {t.id: t for t in problem.teachers}
    room_map: dict[str, Room] = {r.id: r for r in problem.rooms}
    slot_map: dict[str, TimeSlot] = {s.id: s for s in problem.slots}
    session_map: dict[str, Session] = {sess.id: sess for sess in problem.sessions}

    # 1. Verify session coverage (every required session must be scheduled exactly once)
    assigned_session_ids = [a.session_id for a in assignments]
    expected_session_ids = set(session_map.keys())
    seen_session_ids: set[str] = set()

    for sess_id in assigned_session_ids:
        if sess_id not in expected_session_ids:
            violations.append(f"Assignment contains unknown session ID '{sess_id}'.")
        elif sess_id in seen_session_ids:
            violations.append(f"Session '{sess_id}' is scheduled multiple times.")
        else:
            seen_session_ids.add(sess_id)

    missing_sessions = expected_session_ids - seen_session_ids
    if missing_sessions:
        violations.append(f"Required sessions not scheduled: {sorted(missing_sessions)}")

    # 2. Individual assignment validation
    for i, a in enumerate(assignments):
        sess = session_map.get(a.session_id)
        teacher = teacher_map.get(a.teacher_id)
        room = room_map.get(a.room_id)
        slot = slot_map.get(a.slot_id)

        if not sess:
            # Already flagged as unknown session
            continue

        if not teacher:
            violations.append(f"Session '{a.session_id}': assigned non-existent teacher '{a.teacher_id}'.")
        if not room:
            violations.append(f"Session '{a.session_id}': assigned non-existent room '{a.room_id}'.")
        if not slot:
            violations.append(f"Session '{a.session_id}': assigned non-existent slot '{a.slot_id}'.")

        if not (teacher and room and slot):
            continue

        # Check teacher availability
        if slot.id in teacher.unavailable_slots:
            violations.append(
                f"Session '{a.session_id}': Teacher '{teacher.id}' ({teacher.name}) is unavailable at slot '{slot.id}'."
            )

        # Check room availability
        if slot.id in room.unavailable_slots:
            violations.append(
                f"Session '{a.session_id}': Room '{room.id}' ({room.name}) is unavailable at slot '{slot.id}'."
            )

        # Check teacher qualifications
        req_qual = sess.effective_qualification
        if req_qual and req_qual not in teacher.qualifications:
            violations.append(
                f"Session '{a.session_id}': Teacher '{teacher.id}' lacks required qualification '{req_qual}' "
                f"(Teacher qualifications: {teacher.qualifications})."
            )

        # Check room capacity
        if room.capacity < sess.expected_students:
            violations.append(
                f"Session '{a.session_id}': Room '{room.id}' capacity ({room.capacity}) "
                f"is less than expected students ({sess.expected_students})."
            )

        # Check pinning constraints
        if sess.pinned_teacher_id and sess.pinned_teacher_id != teacher.id:
            violations.append(
                f"Session '{a.session_id}': Assigned teacher '{teacher.id}' does not match pinned teacher '{sess.pinned_teacher_id}'."
            )
        if sess.pinned_room_id and sess.pinned_room_id != room.id:
            violations.append(
                f"Session '{a.session_id}': Assigned room '{room.id}' does not match pinned room '{sess.pinned_room_id}'."
            )
        if sess.pinned_slot_id and sess.pinned_slot_id != slot.id:
            violations.append(
                f"Session '{a.session_id}': Assigned slot '{slot.id}' does not match pinned slot '{sess.pinned_slot_id}'."
            )

        # Check allowed sets
        if sess.allowed_teacher_ids is not None and teacher.id not in sess.allowed_teacher_ids:
            violations.append(
                f"Session '{a.session_id}': Teacher '{teacher.id}' is not in allowed teachers {sess.allowed_teacher_ids}."
            )
        if sess.allowed_room_ids is not None and room.id not in sess.allowed_room_ids:
            violations.append(
                f"Session '{a.session_id}': Room '{room.id}' is not in allowed rooms {sess.allowed_room_ids}."
            )
        if sess.allowed_slot_ids is not None and slot.id not in sess.allowed_slot_ids:
            violations.append(
                f"Session '{a.session_id}': Slot '{slot.id}' is not in allowed slots {sess.allowed_slot_ids}."
            )

    # 3. Overlap constraints (no teacher or room double-booking)
    n = len(assignments)
    for i in range(n):
        a1 = assignments[i]
        slot1 = slot_map.get(a1.slot_id)
        if not slot1:
            continue

        for j in range(i + 1, n):
            a2 = assignments[j]
            slot2 = slot_map.get(a2.slot_id)
            if not slot2:
                continue

            # Teacher overlap check
            if a1.teacher_id == a2.teacher_id and slot1.overlaps(slot2):
                violations.append(
                    f"Teacher '{a1.teacher_id}' is double-booked: session '{a1.session_id}' at slot '{slot1.id}' ({slot1.day} {slot1.start_time}-{slot1.end_time}) "
                    f"overlaps with session '{a2.session_id}' at slot '{slot2.id}' ({slot2.day} {slot2.start_time}-{slot2.end_time})."
                )

            # Room overlap check
            if a1.room_id == a2.room_id and slot1.overlaps(slot2):
                violations.append(
                    f"Room '{a1.room_id}' is double-booked: session '{a1.session_id}' at slot '{slot1.id}' ({slot1.day} {slot1.start_time}-{slot1.end_time}) "
                    f"overlaps with session '{a2.session_id}' at slot '{slot2.id}' ({slot2.day} {slot2.start_time}-{slot2.end_time})."
                )

    return len(violations) == 0, violations
