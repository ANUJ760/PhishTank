"""Disruption impact analysis and minimal-change schedule recovery engine."""

from __future__ import annotations

import time
from typing import Any, Sequence
from ortools.sat.python import cp_model

from gecompose.exceptions import SolverError, ValidationError
from gecompose.models import (
    AssignmentChange,
    DisruptionEvent,
    DisruptionRecoveryResult,
    ImpactReport,
    RecoveryPolicy,
    ResourceType,
    Room,
    ScheduledAssignment,
    SchedulingProblem,
    Session,
    SolverStatus,
    Teacher,
    TimeSlot,
)
from gecompose.validator import verify_schedule


def analyze_disruption_impact(
    problem: SchedulingProblem,
    assignments: Sequence[ScheduledAssignment],
    disruption: DisruptionEvent,
) -> ImpactReport:
    """Analyze the direct impact of a disruption event on an active schedule.

    Args:
        problem: Validated SchedulingProblem defining the schedule domain.
        assignments: List of active ScheduledAssignment objects.
        disruption: Validated DisruptionEvent representing resource unavailability.

    Returns:
        ImpactReport detailing directly invalidated sessions, affected assignments,
        and unaffected session IDs.

    Raises:
        ValidationError: If the disruption references unknown resources or slots,
            or if the schedule assignments contain unknown session IDs.
    """
    # Validate problem resource references
    teacher_ids = {t.id for t in problem.teachers}
    room_ids = {r.id for r in problem.rooms}
    slot_ids = {s.id for s in problem.slots}
    session_ids = {s.id for s in problem.sessions}

    if disruption.resource_type == ResourceType.ROOM:
        if disruption.resource_id not in room_ids:
            raise ValidationError(
                f"Disruption '{disruption.id}' references unknown room '{disruption.resource_id}'."
            )
    elif disruption.resource_type == ResourceType.TEACHER:
        if disruption.resource_id not in teacher_ids:
            raise ValidationError(
                f"Disruption '{disruption.id}' references unknown teacher '{disruption.resource_id}'."
            )

    # Validate explicit slot IDs in disruption
    for slot_id in disruption.slot_ids:
        if slot_id not in slot_ids:
            raise ValidationError(
                f"Disruption '{disruption.id}' references unknown slot '{slot_id}'."
            )

    # Validate assignments refer to known sessions
    for a in assignments:
        if a.session_id not in session_ids:
            raise ValidationError(
                f"Schedule contains assignment for unknown session '{a.session_id}'."
            )

    # Resolve all affected slots (combines explicit slot_ids and time interval overlap)
    unavailable_slots = disruption.resolve_unavailable_slots(problem)

    directly_affected_sessions: list[str] = []
    directly_affected_assignments: list[ScheduledAssignment] = []
    unaffected_sessions: list[str] = []

    for a in assignments:
        is_affected = False
        if a.slot_id in unavailable_slots:
            if disruption.resource_type == ResourceType.ROOM and a.room_id == disruption.resource_id:
                is_affected = True
            elif disruption.resource_type == ResourceType.TEACHER and a.teacher_id == disruption.resource_id:
                is_affected = True

        if is_affected:
            directly_affected_sessions.append(a.session_id)
            directly_affected_assignments.append(a)
        else:
            unaffected_sessions.append(a.session_id)

    return ImpactReport(
        disruption=disruption,
        directly_affected_session_ids=directly_affected_sessions,
        directly_affected_assignments=directly_affected_assignments,
        unaffected_session_ids=unaffected_sessions,
        total_scheduled_sessions=len(assignments),
    )


class DisruptionRecoverer:
    """Deterministic CP-SAT schedule recovery optimizer that minimizes changes."""

    def __init__(self, policy: RecoveryPolicy | None = None):
        """Initialize with an optional recovery policy.

        Args:
            policy: RecoveryPolicy specifying weights, reassignments, and timeouts.
        """
        self.policy = policy or RecoveryPolicy()

    def recover(
        self,
        problem: SchedulingProblem,
        assignments: Sequence[ScheduledAssignment],
        disruption: DisruptionEvent,
    ) -> DisruptionRecoveryResult:
        """Compute a minimal-change verified recovery schedule after a disruption.

        Enforces all existing hard constraints (qualifications, capacities, teacher/room
        non-overlap, availability) plus the disruption as hard constraints. Adds a linear
        CP-SAT objective minimizing weighted changes relative to the original schedule,
        strongly protecting unaffected sessions from unnecessary displacement.

        Args:
            problem: Original SchedulingProblem.
            assignments: Current active ScheduledAssignment objects prior to disruption.
            disruption: DisruptionEvent defining unavailable resource and time slots.

        Returns:
            DisruptionRecoveryResult with recovered assignments, change log,
            validation status, and performance statistics.

        Raises:
            ValidationError: If disruption or schedule data is invalid.
            SolverError: If unexpected internal solver errors occur.
        """
        start_time = time.perf_counter()

        # Step 1: Impact analysis and validation
        impact = analyze_disruption_impact(problem, assignments, disruption)
        orig_map: dict[str, ScheduledAssignment] = {a.session_id: a for a in assignments}
        unavailable_slots = disruption.resolve_unavailable_slots(problem)

        # Step 2: Handle trivial case - zero sessions
        if len(problem.sessions) == 0:
            return DisruptionRecoveryResult(
                disruption=disruption,
                status=SolverStatus.OPTIMAL,
                original_assignments=list(assignments),
                recovered_assignments=[],
                directly_affected_session_ids=[],
                moved_session_ids=[],
                unaffected_session_ids=[],
                changes=[],
                total_penalty=0,
                validation_passed=True,
                wall_time_seconds=time.perf_counter() - start_time,
                message="Problem contains zero sessions; empty schedule is trivially valid.",
            )

        # Step 3: Handle zero impact - original schedule unaffected
        if not impact.has_impact:
            # Verify original schedule still satisfies the disruption-augmented problem
            updated_rooms = []
            for r in problem.rooms:
                if disruption.resource_type == ResourceType.ROOM and r.id == disruption.resource_id:
                    updated_rooms.append(
                        Room(
                            id=r.id,
                            name=r.name,
                            capacity=r.capacity,
                            unavailable_slots=r.unavailable_slots | unavailable_slots,
                        )
                    )
                else:
                    updated_rooms.append(r)

            updated_teachers = []
            for t in problem.teachers:
                if disruption.resource_type == ResourceType.TEACHER and t.id == disruption.resource_id:
                    updated_teachers.append(
                        Teacher(
                            id=t.id,
                            name=t.name,
                            qualifications=t.qualifications,
                            unavailable_slots=t.unavailable_slots | unavailable_slots,
                        )
                    )
                else:
                    updated_teachers.append(t)

            updated_problem = SchedulingProblem(
                slots=problem.slots,
                teachers=updated_teachers,
                rooms=updated_rooms,
                sessions=problem.sessions,
            )

            passed, violations = verify_schedule(updated_problem, assignments)
            if passed:
                return DisruptionRecoveryResult(
                    disruption=disruption,
                    status=SolverStatus.OPTIMAL,
                    original_assignments=list(assignments),
                    recovered_assignments=list(assignments),
                    directly_affected_session_ids=[],
                    moved_session_ids=[],
                    unaffected_session_ids=[a.session_id for a in assignments],
                    changes=[],
                    total_penalty=0,
                    validation_passed=True,
                    violations=[],
                    wall_time_seconds=time.perf_counter() - start_time,
                    message="Disruption does not affect any active assignments; original schedule retained.",
                )

        # Step 4: Construct updated resource definitions incorporating disruption
        updated_rooms = []
        for r in problem.rooms:
            if disruption.resource_type == ResourceType.ROOM and r.id == disruption.resource_id:
                updated_rooms.append(
                    Room(
                        id=r.id,
                        name=r.name,
                        capacity=r.capacity,
                        unavailable_slots=r.unavailable_slots | unavailable_slots,
                    )
                )
            else:
                updated_rooms.append(r)

        updated_teachers = []
        for t in problem.teachers:
            if disruption.resource_type == ResourceType.TEACHER and t.id == disruption.resource_id:
                updated_teachers.append(
                    Teacher(
                        id=t.id,
                        name=t.name,
                        qualifications=t.qualifications,
                        unavailable_slots=t.unavailable_slots | unavailable_slots,
                    )
                )
            else:
                updated_teachers.append(t)

        # Update sessions if pinned resource is the disrupted resource and policy allows reassignment
        updated_sessions = []
        for sess in problem.sessions:
            new_pinned_room = sess.pinned_room_id
            new_pinned_teacher = sess.pinned_teacher_id
            new_pinned_slot = sess.pinned_slot_id

            if sess.id in impact.directly_affected_session_ids:
                if disruption.resource_type == ResourceType.ROOM and self.policy.allow_room_reassignment:
                    if sess.pinned_room_id == disruption.resource_id:
                        new_pinned_room = None
                if disruption.resource_type == ResourceType.TEACHER and self.policy.allow_teacher_reassignment:
                    if sess.pinned_teacher_id == disruption.resource_id:
                        new_pinned_teacher = None
                if self.policy.allow_slot_reassignment:
                    if sess.pinned_slot_id in unavailable_slots:
                        new_pinned_slot = None

            updated_sessions.append(
                Session(
                    id=sess.id,
                    title=sess.title,
                    subject=sess.subject,
                    required_qualification=sess.required_qualification,
                    expected_students=sess.expected_students,
                    pinned_teacher_id=new_pinned_teacher,
                    pinned_room_id=new_pinned_room,
                    pinned_slot_id=new_pinned_slot,
                    allowed_teacher_ids=sess.allowed_teacher_ids,
                    allowed_room_ids=sess.allowed_room_ids,
                    allowed_slot_ids=sess.allowed_slot_ids,
                )
            )

        updated_problem = SchedulingProblem(
            slots=problem.slots,
            teachers=updated_teachers,
            rooms=updated_rooms,
            sessions=updated_sessions,
        )

        # Step 5: Build CP-SAT optimization model
        unique_days = sorted(list({s.day.lower() for s in problem.slots}))
        day_to_idx = {d: i for i, d in enumerate(unique_days)}

        model = cp_model.CpModel()
        x_vars: dict[tuple[str, str, str, str], cp_model.IntVar] = {}
        teacher_intervals: dict[str, list[cp_model.IntervalVar]] = {t.id: [] for t in updated_problem.teachers}
        room_intervals: dict[str, list[cp_model.IntervalVar]] = {r.id: [] for r in updated_problem.rooms}

        objective_terms: list[tuple[int, cp_model.IntVar]] = []

        for sess in updated_problem.sessions:
            orig = orig_map.get(sess.id)
            is_directly_affected = sess.id in impact.directly_affected_session_ids
            sess_vars: list[cp_model.IntVar] = []
            req_qual = sess.effective_qualification

            for t in updated_problem.teachers:
                # Hard invariant: Teacher qualification
                if req_qual and req_qual not in t.qualifications:
                    continue
                # Policy check: teacher reassignment
                if not self.policy.allow_teacher_reassignment and orig and t.id != orig.teacher_id:
                    continue
                # Pinned / allowed teachers
                if sess.pinned_teacher_id and sess.pinned_teacher_id != t.id:
                    continue
                if sess.allowed_teacher_ids is not None and t.id not in sess.allowed_teacher_ids:
                    continue

                for r in updated_problem.rooms:
                    # Hard invariant: Room capacity
                    if r.capacity < sess.expected_students:
                        continue
                    # Policy check: room reassignment
                    if not self.policy.allow_room_reassignment and orig and r.id != orig.room_id:
                        continue
                    # Pinned / allowed rooms
                    if sess.pinned_room_id and sess.pinned_room_id != r.id:
                        continue
                    if sess.allowed_room_ids is not None and r.id not in sess.allowed_room_ids:
                        continue

                    for slot in updated_problem.slots:
                        # Hard invariant: Teacher availability (including disruption)
                        if slot.id in t.unavailable_slots:
                            continue
                        # Hard invariant: Room availability (including disruption)
                        if slot.id in r.unavailable_slots:
                            continue
                        # Policy check: slot reassignment
                        if not self.policy.allow_slot_reassignment and orig and slot.id != orig.slot_id:
                            continue
                        # Pinned / allowed slots
                        if sess.pinned_slot_id and sess.pinned_slot_id != slot.id:
                            continue
                        if sess.allowed_slot_ids is not None and slot.id not in sess.allowed_slot_ids:
                            continue

                        # Valid candidate found
                        var = model.NewBoolVar(f"rec_{sess.id}_{t.id}_{r.id}_{slot.id}")
                        x_vars[(sess.id, t.id, r.id, slot.id)] = var
                        sess_vars.append(var)

                        # Time coordinates for interval non-overlap
                        day_offset = day_to_idx[slot.day.lower()] * 1440
                        abs_start = day_offset + slot.start_minute
                        duration = slot.duration_minutes
                        abs_end = abs_start + duration

                        t_iv = model.NewOptionalIntervalVar(
                            abs_start, duration, abs_end, var, f"t_iv_{t.id}_{sess.id}_{slot.id}"
                        )
                        teacher_intervals[t.id].append(t_iv)

                        r_iv = model.NewOptionalIntervalVar(
                            abs_start, duration, abs_end, var, f"r_iv_{r.id}_{sess.id}_{slot.id}"
                        )
                        room_intervals[r.id].append(r_iv)

                        # Calculate penalty weight relative to original assignment
                        penalty = 0
                        if orig:
                            is_identical = (
                                t.id == orig.teacher_id
                                and r.id == orig.room_id
                                and slot.id == orig.slot_id
                            )
                            if not is_identical:
                                # Penalty for displacing an otherwise unaffected session
                                if not is_directly_affected:
                                    penalty += self.policy.unaffected_displacement_penalty

                                if t.id != orig.teacher_id:
                                    penalty += self.policy.teacher_change_penalty
                                if slot.id != orig.slot_id:
                                    penalty += self.policy.slot_change_penalty
                                if r.id != orig.room_id:
                                    penalty += self.policy.room_change_penalty

                        if penalty > 0:
                            objective_terms.append((penalty, var))

            if not sess_vars:
                # Impossible: session has zero valid candidates
                wall_time = time.perf_counter() - start_time
                return DisruptionRecoveryResult(
                    disruption=disruption,
                    status=SolverStatus.INFEASIBLE,
                    original_assignments=list(assignments),
                    recovered_assignments=[],
                    directly_affected_session_ids=impact.directly_affected_session_ids,
                    moved_session_ids=[],
                    unaffected_session_ids=[],
                    changes=[],
                    total_penalty=0,
                    validation_passed=False,
                    wall_time_seconds=wall_time,
                    message=f"Recovery infeasible: session '{sess.id}' has no valid candidate assignment satisfying hard constraints.",
                )

            # Hard constraint: Every session must be scheduled exactly once
            model.AddExactlyOne(sess_vars)

        # Hard constraints: No overlap
        for t_id, intervals in teacher_intervals.items():
            if len(intervals) > 1:
                model.AddNoOverlap(intervals)

        for r_id, intervals in room_intervals.items():
            if len(intervals) > 1:
                model.AddNoOverlap(intervals)

        # Objective: Minimize total change penalty
        if objective_terms:
            model.Minimize(sum(p * v for p, v in objective_terms))
        else:
            model.Minimize(0)

        # Step 6: Solve CP-SAT
        solver = cp_model.CpSolver()
        solver.parameters.max_time_in_seconds = self.policy.time_limit_seconds
        solver.parameters.num_workers = 1

        solve_status = solver.Solve(model)
        wall_time = solver.WallTime()

        if solve_status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            status_enum = (
                SolverStatus.OPTIMAL if solve_status == cp_model.OPTIMAL else SolverStatus.FEASIBLE
            )
            recovered_assignments: list[ScheduledAssignment] = []
            for (s_id, t_id, r_id, slot_id), var in x_vars.items():
                if solver.Value(var) == 1:
                    recovered_assignments.append(
                        ScheduledAssignment(
                            session_id=s_id,
                            teacher_id=t_id,
                            room_id=r_id,
                            slot_id=slot_id,
                        )
                    )

            # Build changes log
            changes: list[AssignmentChange] = []
            moved_sessions: list[str] = []
            unaffected_sessions: list[str] = []
            total_penalty_computed = 0

            for rec in recovered_assignments:
                orig = orig_map.get(rec.session_id)
                if not orig:
                    continue

                ch_t = rec.teacher_id != orig.teacher_id
                ch_r = rec.room_id != orig.room_id
                ch_s = rec.slot_id != orig.slot_id

                if ch_t or ch_r or ch_s:
                    moved_sessions.append(rec.session_id)
                    if rec.session_id in impact.directly_affected_session_ids:
                        reason = (
                            f"Relocated due to disruption '{disruption.id}' "
                            f"({disruption.resource_type.value} '{disruption.resource_id}' unavailable)"
                        )
                    else:
                        reason = "Displaced to accommodate recovery schedule (minimal cascade relocation)"

                    changes.append(
                        AssignmentChange(
                            session_id=rec.session_id,
                            original_assignment=orig,
                            new_assignment=rec,
                            changed_teacher=ch_t,
                            changed_room=ch_r,
                            changed_slot=ch_s,
                            reason=reason,
                        )
                    )
                else:
                    unaffected_sessions.append(rec.session_id)

            if solve_status == cp_model.OPTIMAL:
                total_penalty_computed = int(solver.ObjectiveValue())
            else:
                total_penalty_computed = sum(
                    (self.policy.teacher_change_penalty if c.changed_teacher else 0)
                    + (self.policy.room_change_penalty if c.changed_room else 0)
                    + (self.policy.slot_change_penalty if c.changed_slot else 0)
                    + (self.policy.unaffected_displacement_penalty if c.session_id not in impact.directly_affected_session_ids else 0)
                    for c in changes
                )

            # Step 7: Independent validation
            passed, violations = verify_schedule(updated_problem, recovered_assignments)

            return DisruptionRecoveryResult(
                disruption=disruption,
                status=status_enum,
                original_assignments=list(assignments),
                recovered_assignments=recovered_assignments,
                directly_affected_session_ids=impact.directly_affected_session_ids,
                moved_session_ids=moved_sessions,
                unaffected_session_ids=unaffected_sessions,
                changes=changes,
                total_penalty=total_penalty_computed,
                validation_passed=passed,
                violations=violations,
                wall_time_seconds=wall_time,
                message=(
                    f"Successfully computed recovery schedule with {len(changes)} modification(s) "
                    f"and penalty {total_penalty_computed}."
                    if passed
                    else "Solver generated schedule but independent verification failed."
                ),
                statistics={
                    "total_sessions": len(problem.sessions),
                    "directly_affected": len(impact.directly_affected_session_ids),
                    "displaced_unaffected": len(moved_sessions) - len(impact.directly_affected_session_ids),
                    "objective_value": total_penalty_computed,
                    "cp_sat_status": solver.StatusName(solve_status),
                },
            )

        elif solve_status == cp_model.INFEASIBLE:
            return DisruptionRecoveryResult(
                disruption=disruption,
                status=SolverStatus.INFEASIBLE,
                original_assignments=list(assignments),
                recovered_assignments=[],
                directly_affected_session_ids=impact.directly_affected_session_ids,
                moved_session_ids=[],
                unaffected_session_ids=[],
                changes=[],
                total_penalty=0,
                validation_passed=False,
                wall_time_seconds=wall_time,
                message="Recovery schedule is mathematically infeasible under given constraints and available resources.",
                statistics={"cp_sat_status": "INFEASIBLE"},
            )

        elif solve_status == cp_model.UNKNOWN:
            return DisruptionRecoveryResult(
                disruption=disruption,
                status=SolverStatus.TIMEOUT,
                original_assignments=list(assignments),
                recovered_assignments=[],
                directly_affected_session_ids=impact.directly_affected_session_ids,
                moved_session_ids=[],
                unaffected_session_ids=[],
                changes=[],
                total_penalty=0,
                validation_passed=False,
                wall_time_seconds=wall_time,
                message="Solver timed out before finding a feasible recovery schedule.",
                statistics={"cp_sat_status": "TIMEOUT / UNKNOWN"},
            )

        else:
            return DisruptionRecoveryResult(
                disruption=disruption,
                status=SolverStatus.UNKNOWN,
                original_assignments=list(assignments),
                recovered_assignments=[],
                directly_affected_session_ids=impact.directly_affected_session_ids,
                moved_session_ids=[],
                unaffected_session_ids=[],
                changes=[],
                total_penalty=0,
                validation_passed=False,
                wall_time_seconds=wall_time,
                message=f"Solver returned unhandled status {solver.StatusName(solve_status)}.",
                statistics={"cp_sat_status": solver.StatusName(solve_status)},
            )


def recover_from_disruption(
    problem: SchedulingProblem,
    assignments: Sequence[ScheduledAssignment],
    disruption: DisruptionEvent,
    *,
    policy: RecoveryPolicy | None = None,
) -> DisruptionRecoveryResult:
    """Convenience helper to compute a verified minimal-change recovery schedule."""
    recoverer = DisruptionRecoverer(policy=policy)
    return recoverer.recover(problem, assignments, disruption)
