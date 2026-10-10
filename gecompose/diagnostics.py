"""Conflict diagnosis and Minimal Unsatisfiable Subset (MUS) extraction engine."""

from __future__ import annotations

import time
from typing import Any
from ortools.sat.python import cp_model

from gecompose.models import (
    ConflictConstraint,
    ConflictDiagnosis,
    ConstraintType,
    Room,
    SchedulingProblem,
    Session,
    SolverStatus,
    Teacher,
    TimeSlot,
)


class ConflictDiagnoser:
    """Diagnoses infeasibility in scheduling problems using CP-SAT assumption literals and MUS extraction."""

    def __init__(self, timeout_seconds: float = 5.0, minimize_core: bool = True):
        """Initialize the conflict diagnoser.

        Args:
            timeout_seconds: Total time limit for diagnostic solving and core minimization.
            minimize_core: Whether to perform deletion-based core reduction to guarantee a minimal core (MUS).
        """
        self.timeout_seconds = max(0.001, float(timeout_seconds))
        self.minimize_core = bool(minimize_core)

    def diagnose(self, problem: SchedulingProblem) -> ConflictDiagnosis:
        """Diagnose infeasibility for the given scheduling problem.

        Args:
            problem: Validated SchedulingProblem instance.

        Returns:
            ConflictDiagnosis with status, conflict core, minimality indicator, and fact-grounded explanation.
        """
        start_time = time.perf_counter()

        # Handle trivial zero sessions case
        if len(problem.sessions) == 0:
            return ConflictDiagnosis(
                status=SolverStatus.OPTIMAL,
                is_infeasible=False,
                is_minimal=True,
                explanation="Problem contains zero sessions; no conflicts exist.",
                wall_time_seconds=time.perf_counter() - start_time,
            )

        # Handle empty resource pools
        if len(problem.teachers) == 0 or len(problem.rooms) == 0 or len(problem.slots) == 0:
            conflicts = []
            missing = []
            if len(problem.teachers) == 0:
                missing.append("teachers")
            if len(problem.rooms) == 0:
                missing.append("rooms")
            if len(problem.slots) == 0:
                missing.append("time slots")

            desc = f"Problem is missing necessary resource pools: {', '.join(missing)}."
            conflicts.append(
                ConflictConstraint(
                    id="req_empty_resources",
                    constraint_type=ConstraintType.SESSION_REQUIRED,
                    description=desc,
                )
            )
            return ConflictDiagnosis(
                status=SolverStatus.INFEASIBLE,
                is_infeasible=True,
                is_minimal=True,
                conflicting_constraints=conflicts,
                explanation=desc,
                wall_time_seconds=time.perf_counter() - start_time,
            )

        # Build diagnostic CP-SAT model with assumption literals
        model = cp_model.CpModel()

        # Decision variables: x[s_id, t_id, r_id, slot_id] -> BoolVar
        x_vars: dict[tuple[str, str, str, str], cp_model.IntVar] = {}
        for s in problem.sessions:
            for t in problem.teachers:
                for r in problem.rooms:
                    for slot in problem.slots:
                        x_vars[(s.id, t.id, r.id, slot.id)] = model.NewBoolVar(
                            f"x_{s.id}_{t.id}_{r.id}_{slot.id}"
                        )

        assumptions: list[cp_model.IntVar] = []
        var_to_constraint: dict[int, ConflictConstraint] = {}

        def add_assumption(
            var_name: str,
            c_type: ConstraintType,
            description: str,
            session_id: str | None = None,
            teacher_id: str | None = None,
            room_id: str | None = None,
            slot_id: str | None = None,
            details: dict[str, Any] | None = None,
        ) -> cp_model.IntVar:
            var = model.NewBoolVar(var_name)
            c = ConflictConstraint(
                id=var_name,
                constraint_type=c_type,
                description=description,
                session_id=session_id,
                teacher_id=teacher_id,
                room_id=room_id,
                slot_id=slot_id,
                details=details or {},
            )
            assumptions.append(var)
            var_to_constraint[var.Index()] = c
            return var

        # 1. Session requirement: Each session must be assigned exactly once
        for s in problem.sessions:
            a_sess = add_assumption(
                f"req_session_{s.id}",
                ConstraintType.SESSION_REQUIRED,
                f"Session '{s.id}' ({s.title or s.subject or 'Session'}) must be scheduled exactly once",
                session_id=s.id,
            )
            all_sess_vars = [
                x_vars[(s.id, t.id, r.id, slot.id)]
                for t in problem.teachers
                for r in problem.rooms
                for slot in problem.slots
            ]
            model.Add(sum(all_sess_vars) == 1).OnlyEnforceIf(a_sess)
            model.Add(sum(all_sess_vars) <= 1)

            # 2. Pinned & Allowed Teacher
            if s.pinned_teacher_id:
                a_pin_t = add_assumption(
                    f"req_pin_teacher_{s.id}_{s.pinned_teacher_id}",
                    ConstraintType.PINNED_TEACHER,
                    f"Session '{s.id}' is pinned to Teacher '{s.pinned_teacher_id}'",
                    session_id=s.id,
                    teacher_id=s.pinned_teacher_id,
                )
                other_t_vars = [
                    x_vars[(s.id, t.id, r.id, slot.id)]
                    for t in problem.teachers
                    if t.id != s.pinned_teacher_id
                    for r in problem.rooms
                    for slot in problem.slots
                ]
                if other_t_vars:
                    model.Add(sum(other_t_vars) == 0).OnlyEnforceIf(a_pin_t)

            elif s.allowed_teacher_ids is not None:
                a_allow_t = add_assumption(
                    f"req_allowed_teachers_{s.id}",
                    ConstraintType.ALLOWED_TEACHERS,
                    f"Session '{s.id}' is restricted to allowed teachers: {sorted(s.allowed_teacher_ids)}",
                    session_id=s.id,
                )
                disallowed_t_vars = [
                    x_vars[(s.id, t.id, r.id, slot.id)]
                    for t in problem.teachers
                    if t.id not in s.allowed_teacher_ids
                    for r in problem.rooms
                    for slot in problem.slots
                ]
                if disallowed_t_vars:
                    model.Add(sum(disallowed_t_vars) == 0).OnlyEnforceIf(a_allow_t)

            # 3. Pinned & Allowed Room
            if s.pinned_room_id:
                a_pin_r = add_assumption(
                    f"req_pin_room_{s.id}_{s.pinned_room_id}",
                    ConstraintType.PINNED_ROOM,
                    f"Session '{s.id}' is pinned to Room '{s.pinned_room_id}'",
                    session_id=s.id,
                    room_id=s.pinned_room_id,
                )
                other_r_vars = [
                    x_vars[(s.id, t.id, r.id, slot.id)]
                    for t in problem.teachers
                    for r in problem.rooms
                    if r.id != s.pinned_room_id
                    for slot in problem.slots
                ]
                if other_r_vars:
                    model.Add(sum(other_r_vars) == 0).OnlyEnforceIf(a_pin_r)

            elif s.allowed_room_ids is not None:
                a_allow_r = add_assumption(
                    f"req_allowed_rooms_{s.id}",
                    ConstraintType.ALLOWED_ROOMS,
                    f"Session '{s.id}' is restricted to allowed rooms: {sorted(s.allowed_room_ids)}",
                    session_id=s.id,
                )
                disallowed_r_vars = [
                    x_vars[(s.id, t.id, r.id, slot.id)]
                    for t in problem.teachers
                    for r in problem.rooms
                    if r.id not in s.allowed_room_ids
                    for slot in problem.slots
                ]
                if disallowed_r_vars:
                    model.Add(sum(disallowed_r_vars) == 0).OnlyEnforceIf(a_allow_r)

            # 4. Pinned & Allowed Slot
            if s.pinned_slot_id:
                a_pin_slot = add_assumption(
                    f"req_pin_slot_{s.id}_{s.pinned_slot_id}",
                    ConstraintType.PINNED_SLOT,
                    f"Session '{s.id}' is pinned to TimeSlot '{s.pinned_slot_id}'",
                    session_id=s.id,
                    slot_id=s.pinned_slot_id,
                )
                other_slot_vars = [
                    x_vars[(s.id, t.id, r.id, slot.id)]
                    for t in problem.teachers
                    for r in problem.rooms
                    for slot in problem.slots
                    if slot.id != s.pinned_slot_id
                ]
                if other_slot_vars:
                    model.Add(sum(other_slot_vars) == 0).OnlyEnforceIf(a_pin_slot)

            elif s.allowed_slot_ids is not None:
                a_allow_slot = add_assumption(
                    f"req_allowed_slots_{s.id}",
                    ConstraintType.ALLOWED_SLOTS,
                    f"Session '{s.id}' is restricted to allowed slots: {sorted(s.allowed_slot_ids)}",
                    session_id=s.id,
                )
                disallowed_slot_vars = [
                    x_vars[(s.id, t.id, r.id, slot.id)]
                    for t in problem.teachers
                    for r in problem.rooms
                    for slot in problem.slots
                    if slot.id not in s.allowed_slot_ids
                ]
                if disallowed_slot_vars:
                    model.Add(sum(disallowed_slot_vars) == 0).OnlyEnforceIf(a_allow_slot)

            # 5. Teacher Qualification
            req_qual = s.effective_qualification
            if req_qual:
                unqualified_t_vars = [
                    x_vars[(s.id, t.id, r.id, slot.id)]
                    for t in problem.teachers
                    if req_qual not in t.qualifications
                    for r in problem.rooms
                    for slot in problem.slots
                ]
                if unqualified_t_vars:
                    a_qual = add_assumption(
                        f"req_qual_{s.id}_{req_qual}",
                        ConstraintType.TEACHER_QUALIFICATION,
                        f"Session '{s.id}' requires instructor qualification '{req_qual}'",
                        session_id=s.id,
                        details={"required_qualification": req_qual},
                    )
                    model.Add(sum(unqualified_t_vars) == 0).OnlyEnforceIf(a_qual)

            # 6. Room Capacity
            if s.expected_students > 0:
                under_cap_r_vars = [
                    x_vars[(s.id, t.id, r.id, slot.id)]
                    for t in problem.teachers
                    for r in problem.rooms
                    if r.capacity < s.expected_students
                    for slot in problem.slots
                ]
                if under_cap_r_vars:
                    a_cap = add_assumption(
                        f"req_cap_{s.id}_{s.expected_students}",
                        ConstraintType.ROOM_CAPACITY,
                        f"Session '{s.id}' requires room capacity >= {s.expected_students}",
                        session_id=s.id,
                        details={"expected_students": s.expected_students},
                    )
                    model.Add(sum(under_cap_r_vars) == 0).OnlyEnforceIf(a_cap)

        # 7. Teacher Availability
        for t in problem.teachers:
            for unavail_slot_id in t.unavailable_slots:
                t_unavail_vars = [
                    x_vars[(s.id, t.id, r.id, unavail_slot_id)]
                    for s in problem.sessions
                    for r in problem.rooms
                ]
                if t_unavail_vars:
                    a_t_unavail = add_assumption(
                        f"req_t_unavail_{t.id}_{unavail_slot_id}",
                        ConstraintType.TEACHER_UNAVAILABLE,
                        f"Teacher '{t.id}' ({t.name}) is unavailable at TimeSlot '{unavail_slot_id}'",
                        teacher_id=t.id,
                        slot_id=unavail_slot_id,
                    )
                    model.Add(sum(t_unavail_vars) == 0).OnlyEnforceIf(a_t_unavail)

        # 8. Room Availability
        for r in problem.rooms:
            for unavail_slot_id in r.unavailable_slots:
                r_unavail_vars = [
                    x_vars[(s.id, t.id, r.id, unavail_slot_id)]
                    for s in problem.sessions
                    for t in problem.teachers
                ]
                if r_unavail_vars:
                    a_r_unavail = add_assumption(
                        f"req_r_unavail_{r.id}_{unavail_slot_id}",
                        ConstraintType.ROOM_UNAVAILABLE,
                        f"Room '{r.id}' ({r.name}) is unavailable at TimeSlot '{unavail_slot_id}'",
                        room_id=r.id,
                        slot_id=unavail_slot_id,
                    )
                    model.Add(sum(r_unavail_vars) == 0).OnlyEnforceIf(a_r_unavail)

        # 9. Teacher Non-Overlap
        slot_map = {slot.id: slot for slot in problem.slots}
        for t in problem.teachers:
            a_t_no_overlap = add_assumption(
                f"req_t_no_overlap_{t.id}",
                ConstraintType.TEACHER_NON_OVERLAP,
                f"Teacher '{t.id}' ({t.name}) cannot teach overlapping sessions",
                teacher_id=t.id,
            )
            # Add pairwise non-overlap across overlapping slots
            for i, s1 in enumerate(problem.sessions):
                for s2 in problem.sessions[i + 1 :]:
                    for k1_id, slot1 in slot_map.items():
                        for k2_id, slot2 in slot_map.items():
                            if slot1.overlaps(slot2):
                                for r1 in problem.rooms:
                                    for r2 in problem.rooms:
                                        model.Add(
                                            x_vars[(s1.id, t.id, r1.id, k1_id)]
                                            + x_vars[(s2.id, t.id, r2.id, k2_id)]
                                            <= 1
                                        ).OnlyEnforceIf(a_t_no_overlap)

        # 10. Room Non-Overlap
        for r in problem.rooms:
            a_r_no_overlap = add_assumption(
                f"req_r_no_overlap_{r.id}",
                ConstraintType.ROOM_NON_OVERLAP,
                f"Room '{r.id}' ({r.name}) cannot host overlapping sessions",
                room_id=r.id,
            )
            for i, s1 in enumerate(problem.sessions):
                for s2 in problem.sessions[i + 1 :]:
                    for k1_id, slot1 in slot_map.items():
                        for k2_id, slot2 in slot_map.items():
                            if slot1.overlaps(slot2):
                                for t1 in problem.teachers:
                                    for t2 in problem.teachers:
                                        model.Add(
                                            x_vars[(s1.id, t1.id, r.id, k1_id)]
                                            + x_vars[(s2.id, t2.id, r.id, k2_id)]
                                            <= 1
                                        ).OnlyEnforceIf(a_r_no_overlap)

        # Solve with full assumptions
        solver = cp_model.CpSolver()
        remaining_time = max(0.01, self.timeout_seconds - (time.perf_counter() - start_time))
        solver.parameters.max_time_in_seconds = remaining_time
        model.ClearAssumptions()
        model.AddAssumptions(assumptions)

        status = solver.Solve(model)
        elapsed = time.perf_counter() - start_time

        if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            return ConflictDiagnosis(
                status=SolverStatus.FEASIBLE,
                is_infeasible=False,
                is_minimal=True,
                conflicting_constraints=[],
                explanation="The scheduling problem is feasible; no conflicting constraints exist.",
                wall_time_seconds=elapsed,
            )

        if status != cp_model.INFEASIBLE:
            # UNKNOWN or TIMEOUT
            return ConflictDiagnosis(
                status=SolverStatus.TIMEOUT if elapsed >= self.timeout_seconds - 0.5 else SolverStatus.UNKNOWN,
                is_infeasible=False,
                is_minimal=False,
                conflicting_constraints=[],
                explanation="Diagnostic solver timed out or returned unknown before determining infeasibility.",
                wall_time_seconds=elapsed,
            )

        # Problem is proven INFEASIBLE under assumptions
        raw_core_indices = solver.SufficientAssumptionsForInfeasibility()
        
        # Map raw indices to model variables
        raw_core_vars = [model.GetBoolVarFromProtoIndex(idx) for idx in raw_core_indices]
        
        # Minimization (MUS extraction)
        is_minimal = False
        current_core_vars = list(raw_core_vars)

        if self.minimize_core and len(current_core_vars) > 1:
            i = 0
            while i < len(current_core_vars):
                rem_time = max(0.01, self.timeout_seconds - (time.perf_counter() - start_time))
                if rem_time <= 0.05:
                    break
                solver.parameters.max_time_in_seconds = rem_time
                candidate = current_core_vars[:i] + current_core_vars[i + 1 :]
                model.ClearAssumptions()
                model.AddAssumptions(candidate)
                sub_status = solver.Solve(model)
                if sub_status == cp_model.INFEASIBLE:
                    # candidate subset is sufficient, so current_core_vars[i] was redundant
                    current_core_vars = candidate
                else:
                    # current_core_vars[i] is essential to infeasibility
                    i += 1
            if i == len(current_core_vars):
                is_minimal = True
        elif len(current_core_vars) <= 1:
            is_minimal = True

        # Build structured ConflictConstraint objects
        conflicts: list[ConflictConstraint] = []
        sessions_involved: set[str] = set()
        teachers_involved: set[str] = set()
        rooms_involved: set[str] = set()
        slots_involved: set[str] = set()

        for var in current_core_vars:
            c = var_to_constraint.get(var.Index())
            if c:
                conflicts.append(c)
                if c.session_id:
                    sessions_involved.add(c.session_id)
                if c.teacher_id:
                    teachers_involved.add(c.teacher_id)
                if c.room_id:
                    rooms_involved.add(c.room_id)
                if c.slot_id:
                    slots_involved.add(c.slot_id)

        explanation = self._generate_explanation(problem, conflicts)

        return ConflictDiagnosis(
            status=SolverStatus.INFEASIBLE,
            is_infeasible=True,
            is_minimal=is_minimal,
            conflicting_constraints=conflicts,
            explanation=explanation,
            diagnosed_entities={
                "sessions": sorted(sessions_involved),
                "teachers": sorted(teachers_involved),
                "rooms": sorted(rooms_involved),
                "slots": sorted(slots_involved),
            },
            statistics={
                "num_assumptions": len(assumptions),
                "raw_core_size": len(raw_core_indices),
                "minimal_core_size": len(conflicts),
                "is_minimal": is_minimal,
            },
            wall_time_seconds=time.perf_counter() - start_time,
        )

    def _generate_explanation(
        self, problem: SchedulingProblem, conflicts: list[ConflictConstraint]
    ) -> str:
        """Generate a deterministic, fact-grounded explanation from the conflict constraints."""
        if not conflicts:
            return "The problem is mathematically infeasible under the given constraints."

        sentences: list[str] = []
        c_types = {c.constraint_type for c in conflicts}

        # Check for teacher availability clash
        t_unavail = [c for c in conflicts if c.constraint_type == ConstraintType.TEACHER_UNAVAILABLE]
        pinned_slots = [c for c in conflicts if c.constraint_type == ConstraintType.PINNED_SLOT]
        pinned_teachers = [c for c in conflicts if c.constraint_type == ConstraintType.PINNED_TEACHER]
        
        if t_unavail and (pinned_slots or pinned_teachers):
            for u in t_unavail:
                for ps in pinned_slots:
                    if u.slot_id == ps.slot_id:
                        sentences.append(
                            f"Session '{ps.session_id}' is pinned to slot '{ps.slot_id}', but Teacher '{u.teacher_id}' is unavailable at that time."
                        )

        # Check for room availability clash
        r_unavail = [c for c in conflicts if c.constraint_type == ConstraintType.ROOM_UNAVAILABLE]
        pinned_rooms = [c for c in conflicts if c.constraint_type == ConstraintType.PINNED_ROOM]
        if r_unavail and (pinned_slots or pinned_rooms):
            for u in r_unavail:
                for ps in pinned_slots:
                    if u.slot_id == ps.slot_id:
                        sentences.append(
                            f"Session '{ps.session_id}' is pinned to slot '{ps.slot_id}', but Room '{u.room_id}' is unavailable at that time."
                        )

        # Check for teacher overlap
        t_overlap = [c for c in conflicts if c.constraint_type == ConstraintType.TEACHER_NON_OVERLAP]
        if t_overlap:
            sess_ids = [c.session_id for c in conflicts if c.session_id]
            for to in t_overlap:
                sentences.append(
                    f"Teacher '{to.teacher_id}' is assigned to multiple overlapping sessions ({', '.join(sess_ids) or 'multiple'}), violating the teacher non-overlap constraint."
                )

        # Check for room overlap
        r_overlap = [c for c in conflicts if c.constraint_type == ConstraintType.ROOM_NON_OVERLAP]
        if r_overlap:
            sess_ids = [c.session_id for c in conflicts if c.session_id]
            for ro in r_overlap:
                sentences.append(
                    f"Room '{ro.room_id}' is assigned to multiple overlapping sessions ({', '.join(sess_ids) or 'multiple'}), violating the room non-overlap constraint."
                )

        # Check for qualification shortage
        qual_conflicts = [c for c in conflicts if c.constraint_type == ConstraintType.TEACHER_QUALIFICATION]
        for qc in qual_conflicts:
            sentences.append(
                f"Session '{qc.session_id}' requires qualification '{qc.details.get('required_qualification')}', but no available teacher holds this qualification."
            )

        # Check for capacity shortage
        cap_conflicts = [c for c in conflicts if c.constraint_type == ConstraintType.ROOM_CAPACITY]
        for cc in cap_conflicts:
            sentences.append(
                f"Session '{cc.session_id}' requires a room with capacity >= {cc.details.get('expected_students')}, but no available room meets this requirement."
            )

        if not sentences:
            # Fallback to listing descriptions
            descs = [f"- {c.description}" for c in conflicts]
            return "Conflict detected among the following jointly unsatisfiable requirements:\n" + "\n".join(descs)

        return "Conflict detected: " + " ".join(sentences)


def diagnose_conflicts(
    problem: SchedulingProblem,
    timeout_seconds: float = 5.0,
    minimize_core: bool = True,
) -> ConflictDiagnosis:
    """Convenience function to diagnose infeasibility in a scheduling problem.

    Args:
        problem: Validated SchedulingProblem instance.
        timeout_seconds: Maximum time in seconds.
        minimize_core: Whether to reduce to a minimal unsatisfiable core.

    Returns:
        ConflictDiagnosis.
    """
    diagnoser = ConflictDiagnoser(timeout_seconds=timeout_seconds, minimize_core=minimize_core)
    return diagnoser.diagnose(problem)
