"""Alternative schedule generator for resolving conflicts via minimal relaxations."""

from __future__ import annotations

import time
from typing import Any
from ortools.sat.python import cp_model

from gecompose.models import (
    AlternativeSearchResult,
    ConstraintType,
    RelaxationPolicy,
    RelaxedRequirement,
    Room,
    ScheduleAlternative,
    ScheduledAssignment,
    SchedulingProblem,
    Session,
    SolverStatus,
    Teacher,
    TimeSlot,
)
from gecompose.validator import verify_schedule


class AlternativeGenerator:
    """Generates solver-verified alternative schedules by relaxing soft/pinned user requirements."""

    def __init__(self, policy: RelaxationPolicy | None = None):
        """Initialize the alternative generator with relaxation policy."""
        self.policy = policy or RelaxationPolicy()

    def generate(self, problem: SchedulingProblem) -> AlternativeSearchResult:
        """Search for the top alternative schedules that resolve infeasibilities with minimal relaxations.

        Args:
            problem: The original, infeasible SchedulingProblem.

        Returns:
            AlternativeSearchResult containing validated alternatives and relaxation records.
        """
        start_time = time.perf_counter()

        # Handle empty sessions
        if len(problem.sessions) == 0:
            return AlternativeSearchResult(
                status=SolverStatus.OPTIMAL,
                original_status=SolverStatus.OPTIMAL,
                alternatives=[],
                search_time_seconds=time.perf_counter() - start_time,
                message="Problem contains zero sessions; no alternatives needed.",
            )

        # Handle resource exhaustion
        if len(problem.teachers) == 0 or len(problem.rooms) == 0 or len(problem.slots) == 0:
            return AlternativeSearchResult(
                status=SolverStatus.INFEASIBLE,
                original_status=SolverStatus.INFEASIBLE,
                alternatives=[],
                search_time_seconds=time.perf_counter() - start_time,
                message="No resource pools available to construct alternatives.",
            )

        unique_days: list[str] = sorted(list({s.day.lower() for s in problem.slots}))
        day_to_idx: dict[str, int] = {d: i for i, d in enumerate(unique_days)}
        slot_map: dict[str, TimeSlot] = {s.id: s for s in problem.slots}

        model = cp_model.CpModel()

        # Decision variables: x[s, t, r, k] -> BoolVar
        # Only create variables that respect HARD non-negotiable invariants:
        # - Teacher qualification
        # - Room capacity
        # - Teacher unavailability
        # - Room unavailability
        x_vars: dict[tuple[str, str, str, str], cp_model.IntVar] = {}
        teacher_intervals: dict[str, list[cp_model.IntervalVar]] = {t.id: [] for t in problem.teachers}
        room_intervals: dict[str, list[cp_model.IntervalVar]] = {r.id: [] for r in problem.rooms}

        for s in problem.sessions:
            req_qual = s.effective_qualification

            for t in problem.teachers:
                # Hard invariant: Teacher must have qualification
                if req_qual and req_qual not in t.qualifications:
                    continue

                for r in problem.rooms:
                    # Hard invariant: Room capacity must fit expected students
                    if r.capacity < s.expected_students:
                        continue

                    for slot in problem.slots:
                        # Hard invariant: Teacher availability
                        if slot.id in t.unavailable_slots:
                            continue
                        # Hard invariant: Room availability
                        if slot.id in r.unavailable_slots:
                            continue

                        var = model.NewBoolVar(f"x_{s.id}_{t.id}_{r.id}_{slot.id}")
                        x_vars[(s.id, t.id, r.id, slot.id)] = var

                        # Continuous timeline intervals for NoOverlap
                        day_offset = day_to_idx[slot.day.lower()] * 1440
                        abs_start = day_offset + slot.start_minute
                        duration = slot.duration_minutes
                        abs_end = abs_start + duration

                        t_iv = model.NewOptionalIntervalVar(
                            abs_start, duration, abs_end, var, f"alt_t_iv_{t.id}_{s.id}_{slot.id}"
                        )
                        teacher_intervals[t.id].append(t_iv)

                        r_iv = model.NewOptionalIntervalVar(
                            abs_start, duration, abs_end, var, f"alt_r_iv_{r.id}_{s.id}_{slot.id}"
                        )
                        room_intervals[r.id].append(r_iv)

        # Hard invariant: Every session must be scheduled exactly once
        for s in problem.sessions:
            sess_vars = [
                var for (s_id, _, _, _), var in x_vars.items() if s_id == s.id
            ]
            if not sess_vars:
                # A session has zero valid candidates even with all relaxations
                return AlternativeSearchResult(
                    status=SolverStatus.INFEASIBLE,
                    original_status=SolverStatus.INFEASIBLE,
                    alternatives=[],
                    search_time_seconds=time.perf_counter() - start_time,
                    message=f"Session '{s.id}' cannot be scheduled under hard qualification, capacity, or availability constraints.",
                )
            model.AddExactlyOne(sess_vars)

        # Hard invariant: Teacher & Room non-overlap
        for t_id, intervals in teacher_intervals.items():
            if len(intervals) > 1:
                model.AddNoOverlap(intervals)

        for r_id, intervals in room_intervals.items():
            if len(intervals) > 1:
                model.AddNoOverlap(intervals)

        # Track relaxations and penalties
        relaxation_penalties: list[cp_model.IntVar] = []
        
        # Maps for tracking relaxation variables to inspect in solution
        slot_relaxed_vars: dict[str, tuple[cp_model.IntVar, str | None, set[str] | None]] = {}
        teacher_relaxed_vars: dict[str, tuple[cp_model.IntVar, str | None, set[str] | None]] = {}
        room_relaxed_vars: dict[str, tuple[cp_model.IntVar, str | None, set[str] | None]] = {}

        for s in problem.sessions:
            is_eligible = (
                self.policy.relaxable_session_ids is None
                or s.id in self.policy.relaxable_session_ids
            )

            # --- Slot Pinning / Allowed ---
            if s.pinned_slot_id or s.allowed_slot_ids is not None:
                if self.policy.allow_slot_relaxation and is_eligible:
                    rel_slot_var = model.NewBoolVar(f"rel_slot_{s.id}")
                    slot_relaxed_vars[s.id] = (rel_slot_var, s.pinned_slot_id, s.allowed_slot_ids)
                    
                    # Weight: penalty of 1 for slot move
                    relaxation_penalties.append(rel_slot_var)

                    # If not relaxed, enforce pinning/allowed
                    if s.pinned_slot_id:
                        pinned_k = s.pinned_slot_id
                        sum_pinned = sum(
                            var for (s_id, _, _, k_id), var in x_vars.items()
                            if s_id == s.id and k_id == pinned_k
                        )
                        model.Add(sum_pinned == 1).OnlyEnforceIf(rel_slot_var.Not())
                    elif s.allowed_slot_ids is not None:
                        allowed_k = s.allowed_slot_ids
                        sum_allowed = sum(
                            var for (s_id, _, _, k_id), var in x_vars.items()
                            if s_id == s.id and k_id in allowed_k
                        )
                        model.Add(sum_allowed == 1).OnlyEnforceIf(rel_slot_var.Not())
                else:
                    # Non-relaxable slot restriction
                    if s.pinned_slot_id:
                        sum_pinned = sum(
                            var for (s_id, _, _, k_id), var in x_vars.items()
                            if s_id == s.id and k_id == s.pinned_slot_id
                        )
                        model.Add(sum_pinned == 1)
                    elif s.allowed_slot_ids is not None:
                        sum_allowed = sum(
                            var for (s_id, _, _, k_id), var in x_vars.items()
                            if s_id == s.id and k_id in s.allowed_slot_ids
                        )
                        model.Add(sum_allowed == 1)

            # --- Teacher Pinning / Allowed ---
            if s.pinned_teacher_id or s.allowed_teacher_ids is not None:
                if self.policy.allow_teacher_relaxation and is_eligible:
                    rel_t_var = model.NewBoolVar(f"rel_teacher_{s.id}")
                    teacher_relaxed_vars[s.id] = (rel_t_var, s.pinned_teacher_id, s.allowed_teacher_ids)
                    
                    # Weight: penalty of 2 for instructor swap
                    rel_t_weighted = model.NewIntVar(0, 2, f"rel_t_wt_{s.id}")
                    model.Add(rel_t_weighted == rel_t_var * 2)
                    relaxation_penalties.append(rel_t_weighted)

                    if s.pinned_teacher_id:
                        pinned_t = s.pinned_teacher_id
                        sum_pinned = sum(
                            var for (s_id, t_id, _, _), var in x_vars.items()
                            if s_id == s.id and t_id == pinned_t
                        )
                        model.Add(sum_pinned == 1).OnlyEnforceIf(rel_t_var.Not())
                    elif s.allowed_teacher_ids is not None:
                        allowed_t = s.allowed_teacher_ids
                        sum_allowed = sum(
                            var for (s_id, t_id, _, _), var in x_vars.items()
                            if s_id == s.id and t_id in allowed_t
                        )
                        model.Add(sum_allowed == 1).OnlyEnforceIf(rel_t_var.Not())
                else:
                    if s.pinned_teacher_id:
                        sum_pinned = sum(
                            var for (s_id, t_id, _, _), var in x_vars.items()
                            if s_id == s.id and t_id == s.pinned_teacher_id
                        )
                        model.Add(sum_pinned == 1)
                    elif s.allowed_teacher_ids is not None:
                        sum_allowed = sum(
                            var for (s_id, t_id, _, _), var in x_vars.items()
                            if s_id == s.id and t_id in s.allowed_teacher_ids
                        )
                        model.Add(sum_allowed == 1)

            # --- Room Pinning / Allowed ---
            if s.pinned_room_id or s.allowed_room_ids is not None:
                if self.policy.allow_room_relaxation and is_eligible:
                    rel_r_var = model.NewBoolVar(f"rel_room_{s.id}")
                    room_relaxed_vars[s.id] = (rel_r_var, s.pinned_room_id, s.allowed_room_ids)
                    
                    # Weight: penalty of 1 for room relocation
                    relaxation_penalties.append(rel_r_var)

                    if s.pinned_room_id:
                        pinned_r = s.pinned_room_id
                        sum_pinned = sum(
                            var for (s_id, _, r_id, _), var in x_vars.items()
                            if s_id == s.id and r_id == pinned_r
                        )
                        model.Add(sum_pinned == 1).OnlyEnforceIf(rel_r_var.Not())
                    elif s.allowed_room_ids is not None:
                        allowed_r = s.allowed_room_ids
                        sum_allowed = sum(
                            var for (s_id, _, r_id, _), var in x_vars.items()
                            if s_id == s.id and r_id in allowed_r
                        )
                        model.Add(sum_allowed == 1).OnlyEnforceIf(rel_r_var.Not())
                else:
                    if s.pinned_room_id:
                        sum_pinned = sum(
                            var for (s_id, _, r_id, _), var in x_vars.items()
                            if s_id == s.id and r_id == s.pinned_room_id
                        )
                        model.Add(sum_pinned == 1)
                    elif s.allowed_room_ids is not None:
                        sum_allowed = sum(
                            var for (s_id, _, r_id, _), var in x_vars.items()
                            if s_id == s.id and r_id in s.allowed_room_ids
                        )
                        model.Add(sum_allowed == 1)

        # Objective: Minimize total relaxation penalty
        if relaxation_penalties:
            model.Minimize(sum(relaxation_penalties))

        # Iteratively search for up to max_alternatives distinct verified solutions
        solver = cp_model.CpSolver()
        alternatives: list[ScheduleAlternative] = []
        seen_solution_fingerprints: set[frozenset[tuple[str, str, str, str]]] = set()

        for alt_idx in range(1, self.policy.max_alternatives + 1):
            rem_time = max(0.01, self.policy.timeout_seconds - (time.perf_counter() - start_time))
            if rem_time <= 0.05:
                break

            solver.parameters.max_time_in_seconds = rem_time
            status = solver.Solve(model)

            if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
                break

            # Extract assignments
            assignments: list[ScheduledAssignment] = []
            assignment_tuples: list[tuple[str, str, str, str]] = []
            for (s_id, t_id, r_id, k_id), var in x_vars.items():
                if solver.Value(var) == 1:
                    assignments.append(
                        ScheduledAssignment(
                            session_id=s_id, teacher_id=t_id, room_id=r_id, slot_id=k_id
                        )
                    )
                    assignment_tuples.append((s_id, t_id, r_id, k_id))

            fingerprint = frozenset(assignment_tuples)
            if fingerprint in seen_solution_fingerprints:
                break
            seen_solution_fingerprints.add(fingerprint)

            # Identify which requirements were relaxed
            relaxed_records: list[RelaxedRequirement] = []
            for a in assignments:
                # Check slot relaxation
                if a.session_id in slot_relaxed_vars:
                    var, pin_k, allow_k = slot_relaxed_vars[a.session_id]
                    if solver.Value(var) == 1:
                        orig = pin_k or f"allowed {sorted(allow_k or set())}"
                        relaxed_records.append(
                            RelaxedRequirement(
                                session_id=a.session_id,
                                constraint_type=ConstraintType.PINNED_SLOT if pin_k else ConstraintType.ALLOWED_SLOTS,
                                original_value=orig,
                                relaxed_value=a.slot_id,
                                description=f"Relocated session '{a.session_id}' from {orig} to slot '{a.slot_id}'.",
                            )
                        )

                # Check teacher relaxation
                if a.session_id in teacher_relaxed_vars:
                    var, pin_t, allow_t = teacher_relaxed_vars[a.session_id]
                    if solver.Value(var) == 1:
                        orig = pin_t or f"allowed {sorted(allow_t or set())}"
                        relaxed_records.append(
                            RelaxedRequirement(
                                session_id=a.session_id,
                                constraint_type=ConstraintType.PINNED_TEACHER if pin_t else ConstraintType.ALLOWED_TEACHERS,
                                original_value=orig,
                                relaxed_value=a.teacher_id,
                                description=f"Reassigned session '{a.session_id}' from instructor {orig} to '{a.teacher_id}'.",
                            )
                        )

                # Check room relaxation
                if a.session_id in room_relaxed_vars:
                    var, pin_r, allow_r = room_relaxed_vars[a.session_id]
                    if solver.Value(var) == 1:
                        orig = pin_r or f"allowed {sorted(allow_r or set())}"
                        relaxed_records.append(
                            RelaxedRequirement(
                                session_id=a.session_id,
                                constraint_type=ConstraintType.PINNED_ROOM if pin_r else ConstraintType.ALLOWED_ROOMS,
                                original_value=orig,
                                relaxed_value=a.room_id,
                                description=f"Moved session '{a.session_id}' from room {orig} to room '{a.room_id}'.",
                            )
                        )

            # Build relaxed problem representation for independent verification
            relaxed_sessions = []
            rel_by_sess: dict[str, list[RelaxedRequirement]] = {}
            for r in relaxed_records:
                rel_by_sess.setdefault(r.session_id, []).append(r)

            for s in problem.sessions:
                s_dict = s.model_dump()
                sess_rels = rel_by_sess.get(s.id, [])
                for rel in sess_rels:
                    if rel.constraint_type in (ConstraintType.PINNED_SLOT, ConstraintType.ALLOWED_SLOTS):
                        s_dict["pinned_slot_id"] = None
                        s_dict["allowed_slot_ids"] = None
                    elif rel.constraint_type in (ConstraintType.PINNED_TEACHER, ConstraintType.ALLOWED_TEACHERS):
                        s_dict["pinned_teacher_id"] = None
                        s_dict["allowed_teacher_ids"] = None
                    elif rel.constraint_type in (ConstraintType.PINNED_ROOM, ConstraintType.ALLOWED_ROOMS):
                        s_dict["pinned_room_id"] = None
                        s_dict["allowed_room_ids"] = None
                relaxed_sessions.append(Session(**s_dict))

            relaxed_problem = SchedulingProblem(
                teachers=problem.teachers,
                rooms=problem.rooms,
                slots=problem.slots,
                sessions=relaxed_sessions,
            )

            # Independent validation check
            is_valid, violations = verify_schedule(relaxed_problem, assignments)
            if not is_valid:
                # Discard invalid solution
                continue

            penalty = int(solver.ObjectiveValue()) if relaxation_penalties else 0

            alternative = ScheduleAlternative(
                alternative_id=len(alternatives) + 1,
                assignments=assignments,
                relaxed_requirements=relaxed_records,
                penalty_score=penalty,
                validation_passed=True,
                status=SolverStatus.FEASIBLE,
            )
            alternatives.append(alternative)

            # Block the exact current solution to find the next distinct alternative
            active_vars = [x_vars[tup] for tup in assignment_tuples]
            model.Add(sum(active_vars) <= len(problem.sessions) - 1)

        search_time = time.perf_counter() - start_time
        status = SolverStatus.FEASIBLE if len(alternatives) > 0 else SolverStatus.INFEASIBLE
        msg = (
            f"Successfully found {len(alternatives)} solver-verified alternative schedule(s)."
            if len(alternatives) > 0
            else "No feasible alternatives found under the configured relaxation policy."
        )

        return AlternativeSearchResult(
            status=status,
            original_status=SolverStatus.INFEASIBLE,
            alternatives=alternatives,
            search_time_seconds=search_time,
            message=msg,
            statistics={"num_alternatives": len(alternatives)},
        )


def generate_alternatives(
    problem: SchedulingProblem, policy: RelaxationPolicy | None = None
) -> AlternativeSearchResult:
    """Convenience function to generate solver-verified alternative schedules.

    Args:
        problem: Infeasible SchedulingProblem instance.
        policy: Optional RelaxationPolicy specifying what may be relaxed.

    Returns:
        AlternativeSearchResult with verified alternatives.
    """
    generator = AlternativeGenerator(policy=policy)
    return generator.generate(problem)
