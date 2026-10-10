"""CP-SAT based deterministic scheduling engine for GeCompose."""

from __future__ import annotations

import time
from typing import Any
from ortools.sat.python import cp_model

from gecompose.models import (
    Room,
    ScheduledAssignment,
    ScheduleResult,
    SchedulingProblem,
    Session,
    SolverStatus,
    Teacher,
    TimeSlot,
)
from gecompose.validator import verify_schedule


class CPSATScheduler:
    """Deterministic constraint satisfaction scheduler using Google OR-Tools CP-SAT."""

    def __init__(
        self,
        time_limit_seconds: float = 10.0,
        num_workers: int = 1,
        log_search_progress: bool = False,
    ):
        """Initialize the scheduler with solver configuration.

        Args:
            time_limit_seconds: Maximum wall time allotted for the solver in seconds.
            num_workers: Number of parallel search workers for CP-SAT.
            log_search_progress: Whether to log search progress to stdout.
        """
        self.time_limit_seconds = max(0.001, float(time_limit_seconds))
        self.num_workers = max(1, int(num_workers))
        self.log_search_progress = bool(log_search_progress)

    def solve(self, problem: SchedulingProblem) -> ScheduleResult:
        """Solve the scheduling problem and enforce all hard constraints.

        Args:
            problem: Validated SchedulingProblem containing teachers, rooms, slots, and sessions.

        Returns:
            ScheduleResult containing the solver status, verified assignments (if feasible/optimal),
            solve wall time, and independent verification flags.
        """
        start_time = time.perf_counter()

        # Handle trivial case: no sessions to schedule
        if len(problem.sessions) == 0:
            wall_time = time.perf_counter() - start_time
            return ScheduleResult(
                status=SolverStatus.OPTIMAL,
                assignments=[],
                wall_time_seconds=wall_time,
                validation_passed=True,
                message="Problem contains zero sessions; empty schedule is trivially optimal.",
                statistics={"num_sessions": 0, "num_variables": 0, "num_constraints": 0},
            )

        # Handle insufficient resources
        if len(problem.teachers) == 0 or len(problem.rooms) == 0 or len(problem.slots) == 0:
            wall_time = time.perf_counter() - start_time
            return ScheduleResult(
                status=SolverStatus.INFEASIBLE,
                assignments=[],
                wall_time_seconds=wall_time,
                validation_passed=False,
                message="Cannot schedule sessions: one or more resource pools (teachers, rooms, slots) are empty.",
                statistics={
                    "num_sessions": len(problem.sessions),
                    "num_teachers": len(problem.teachers),
                    "num_rooms": len(problem.rooms),
                    "num_slots": len(problem.slots),
                },
            )

        # Map days to continuous discrete buckets for interval overlap calculations
        unique_days: list[str] = sorted(list({s.day.lower() for s in problem.slots}))
        day_to_idx: dict[str, int] = {d: i for i, d in enumerate(unique_days)}

        # Build CP-SAT Model
        model = cp_model.CpModel()

        # candidate tuples per session: session_id -> list of (Teacher, Room, TimeSlot)
        valid_candidates_by_session: dict[str, list[tuple[Teacher, Room, TimeSlot]]] = {}
        # Decision variables: (session_id, teacher_id, room_id, slot_id) -> cp_model.IntVar (BoolVar)
        x_vars: dict[tuple[str, str, str, str], cp_model.IntVar] = {}

        # Intervals per teacher and room for NoOverlap constraints
        teacher_intervals: dict[str, list[cp_model.IntervalVar]] = {t.id: [] for t in problem.teachers}
        room_intervals: dict[str, list[cp_model.IntervalVar]] = {r.id: [] for r in problem.rooms}

        for sess in problem.sessions:
            candidates: list[tuple[Teacher, Room, TimeSlot]] = []
            req_qual = sess.effective_qualification

            for t in problem.teachers:
                # Check teacher qualification
                if req_qual and req_qual not in t.qualifications:
                    continue
                # Check teacher pinning / allowed
                if sess.pinned_teacher_id and sess.pinned_teacher_id != t.id:
                    continue
                if sess.allowed_teacher_ids is not None and t.id not in sess.allowed_teacher_ids:
                    continue

                for r in problem.rooms:
                    # Check room capacity
                    if r.capacity < sess.expected_students:
                        continue
                    # Check room pinning / allowed
                    if sess.pinned_room_id and sess.pinned_room_id != r.id:
                        continue
                    if sess.allowed_room_ids is not None and r.id not in sess.allowed_room_ids:
                        continue

                    for slot in problem.slots:
                        # Check teacher availability
                        if slot.id in t.unavailable_slots:
                            continue
                        # Check room availability
                        if slot.id in r.unavailable_slots:
                            continue
                        # Check slot pinning / allowed
                        if sess.pinned_slot_id and sess.pinned_slot_id != slot.id:
                            continue
                        if sess.allowed_slot_ids is not None and slot.id not in sess.allowed_slot_ids:
                            continue

                        candidates.append((t, r, slot))

            valid_candidates_by_session[sess.id] = candidates

            # Create Boolean decision variables for valid candidates
            sess_vars: list[cp_model.IntVar] = []
            for t, r, slot in candidates:
                var_key = (sess.id, t.id, r.id, slot.id)
                var = model.NewBoolVar(f"x_{sess.id}_{t.id}_{r.id}_{slot.id}")
                x_vars[var_key] = var
                sess_vars.append(var)

                # Construct time interval coordinates
                day_offset = day_to_idx[slot.day.lower()] * 1440
                abs_start = day_offset + slot.start_minute
                duration = slot.duration_minutes
                abs_end = abs_start + duration

                # Optional interval for teacher non-overlap
                t_iv = model.NewOptionalIntervalVar(
                    abs_start,
                    duration,
                    abs_end,
                    var,
                    f"t_iv_{t.id}_{sess.id}_{slot.id}",
                )
                teacher_intervals[t.id].append(t_iv)

                # Optional interval for room non-overlap
                r_iv = model.NewOptionalIntervalVar(
                    abs_start,
                    duration,
                    abs_end,
                    var,
                    f"r_iv_{r.id}_{sess.id}_{slot.id}",
                )
                room_intervals[r.id].append(r_iv)

            # Hard Constraint: Every session must be scheduled exactly once
            model.AddExactlyOne(sess_vars)

        # Hard Constraint: No teacher can teach overlapping sessions
        for t_id, intervals in teacher_intervals.items():
            if len(intervals) > 1:
                model.AddNoOverlap(intervals)

        # Hard Constraint: No room can host overlapping sessions
        for r_id, intervals in room_intervals.items():
            if len(intervals) > 1:
                model.AddNoOverlap(intervals)

        # Configure CP-SAT solver
        solver = cp_model.CpSolver()
        solver.parameters.max_time_in_seconds = self.time_limit_seconds
        solver.parameters.num_workers = self.num_workers
        solver.parameters.log_search_progress = self.log_search_progress

        solve_status = solver.Solve(model)
        wall_time = solver.WallTime()

        stats = {
            "num_sessions": len(problem.sessions),
            "num_teachers": len(problem.teachers),
            "num_rooms": len(problem.rooms),
            "num_slots": len(problem.slots),
            "num_decision_vars": len(x_vars),
            "solver_wall_time": wall_time,
            "cp_sat_status": solver.StatusName(solve_status),
        }

        # Process solver status
        if solve_status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            status_enum = (
                SolverStatus.OPTIMAL if solve_status == cp_model.OPTIMAL else SolverStatus.FEASIBLE
            )

            # Extract assignments
            assignments: list[ScheduledAssignment] = []
            for (s_id, t_id, r_id, slot_id), var in x_vars.items():
                if solver.Value(var) == 1:
                    assignments.append(
                        ScheduledAssignment(
                            session_id=s_id,
                            teacher_id=t_id,
                            room_id=r_id,
                            slot_id=slot_id,
                        )
                    )

            # Run independent verification
            is_valid, violations = verify_schedule(problem, assignments)
            if not is_valid:
                # Never report an unverified or flawed assignment as valid
                return ScheduleResult(
                    status=SolverStatus.UNKNOWN,
                    assignments=[],
                    wall_time_seconds=wall_time,
                    validation_passed=False,
                    violations=violations,
                    message=f"Independent validation failed on solver output: {'; '.join(violations)}",
                    statistics=stats,
                )

            return ScheduleResult(
                status=status_enum,
                assignments=assignments,
                wall_time_seconds=wall_time,
                validation_passed=True,
                violations=[],
                message=f"Schedule successfully solved with status {status_enum.value}.",
                statistics=stats,
            )

        elif solve_status == cp_model.INFEASIBLE:
            return ScheduleResult(
                status=SolverStatus.INFEASIBLE,
                assignments=[],
                wall_time_seconds=wall_time,
                validation_passed=False,
                message="The scheduling problem is mathematically infeasible under the given hard constraints.",
                statistics=stats,
            )

        elif solve_status == cp_model.MODEL_INVALID:
            return ScheduleResult(
                status=SolverStatus.INVALID_INPUT,
                assignments=[],
                wall_time_seconds=wall_time,
                validation_passed=False,
                message="The constructed CP-SAT model was invalid.",
                statistics=stats,
            )

        else:
            # UNKNOWN or timeout
            status_name = (
                SolverStatus.TIMEOUT
                if wall_time >= (self.time_limit_seconds - 0.5)
                else SolverStatus.UNKNOWN
            )
            return ScheduleResult(
                status=status_name,
                assignments=[],
                wall_time_seconds=wall_time,
                validation_passed=False,
                message=f"CP-SAT solver stopped with status {solver.StatusName(solve_status)} without finding a feasible solution.",
                statistics=stats,
            )


    def diagnose(
        self,
        problem: SchedulingProblem,
        timeout_seconds: float | None = None,
        minimize_core: bool = True,
    ):
        """Diagnose infeasibility in the given problem and extract the conflict core.

        Args:
            problem: Validated SchedulingProblem instance.
            timeout_seconds: Timeout for diagnosis (defaults to solver's time_limit_seconds).
            minimize_core: Whether to reduce the core to a minimal unsatisfiable subset.

        Returns:
            ConflictDiagnosis with status, conflict core, and explanation.
        """
        from gecompose.diagnostics import ConflictDiagnoser

        timeout = timeout_seconds or self.time_limit_seconds
        diagnoser = ConflictDiagnoser(timeout_seconds=timeout, minimize_core=minimize_core)
        return diagnoser.diagnose(problem)

    def generate_alternatives(
        self,
        problem: SchedulingProblem,
        policy: RelaxationPolicy | None = None,
    ):
        """Generate solver-verified alternative schedules by relaxing user constraints.

        Args:
            problem: Infeasible SchedulingProblem instance.
            policy: Optional RelaxationPolicy specifying relaxation allowances.

        Returns:
            AlternativeSearchResult with verified alternative schedules.
        """
        from gecompose.alternatives import AlternativeGenerator

        generator = AlternativeGenerator(policy=policy)
        return generator.generate(problem)



def solve_schedule(
    problem: SchedulingProblem,
    time_limit_seconds: float = 10.0,
    num_workers: int = 1,
    log_search_progress: bool = False,
) -> ScheduleResult:
    """Convenience function to solve a scheduling problem.

    Args:
        problem: Validated SchedulingProblem instance.
        time_limit_seconds: Max solver time in seconds.
        num_workers: Number of solver worker threads.
        log_search_progress: Whether to log search progress.

    Returns:
        ScheduleResult with status and verified assignments.
    """
    scheduler = CPSATScheduler(
        time_limit_seconds=time_limit_seconds,
        num_workers=num_workers,
        log_search_progress=log_search_progress,
    )
    return scheduler.solve(problem)

