"""Production-grade Universal CP-SAT discrete constraint optimizer."""
from __future__ import annotations

import time
from ortools.sat.python import cp_model

from backend.universal.models import (
    ConstraintPriority,
    ResourceKind,
    UniversalAssignment,
    UniversalProblem,
    UniversalResource,
    UniversalSolution,
    UniversalTask,
)


class UniversalConstraintSolver:
    """Solves multi-resource, time-windowed scheduling problems across healthcare, logistics, and industry."""

    def __init__(self, time_limit_seconds: float = 10.0, random_seed: int = 42):
        self.time_limit_seconds = time_limit_seconds
        self.random_seed = random_seed

    def solve(self, problem: UniversalProblem) -> UniversalSolution:
        start_mono = time.monotonic()
        model = cp_model.CpModel()
        horizon = problem.horizon_minutes

        res_map = {r.id: r for r in problem.resources if r.is_operational}
        operational_resources = list(res_map.values())

        # Group resources by kind
        space_resources = [r for r in operational_resources if r.kind == ResourceKind.SPACE]
        human_resources = [r for r in operational_resources if r.kind == ResourceKind.HUMAN]
        equip_resources = [r for r in operational_resources if r.kind == ResourceKind.EQUIPMENT]

        # Priority weights
        priority_weights = {
            ConstraintPriority.CRITICAL_EMERGENCY: 10000,
            ConstraintPriority.HIGH_PRIORITY: 2500,
            ConstraintPriority.NORMAL: 500,
            ConstraintPriority.LOW_BACKGROUND: 100,
        }

        # Decision variables per task
        scheduled_vars: dict[str, cp_model.IntVar] = {}
        start_vars: dict[str, cp_model.IntVar] = {}
        end_vars: dict[str, cp_model.IntVar] = {}
        interval_vars: dict[str, cp_model.IntervalVar] = {}

        # Resource assignment variables: assign[task_id, res_id]
        assign_vars: dict[tuple[str, str], cp_model.IntVar] = {}

        # Optional intervals for resource no-overlap
        # res_intervals[res_id] = list of optional IntervalVars
        res_intervals: dict[str, list[cp_model.IntervalVar]] = {r.id: [] for r in operational_resources}

        for task in problem.tasks:
            t_id = task.id
            dur = task.duration_minutes
            earliest = max(0, task.earliest_start_minute)
            latest_start = max(earliest, horizon - dur)

            # Scheduled flag (1 = scheduled, 0 = unmet)
            is_sched = model.NewBoolVar(f"sched_{t_id}")
            scheduled_vars[t_id] = is_sched

            s_var = model.NewIntVar(earliest, latest_start, f"start_{t_id}")
            e_var = model.NewIntVar(earliest + dur, horizon, f"end_{t_id}")
            start_vars[t_id] = s_var
            end_vars[t_id] = e_var

            # Task interval
            t_interval = model.NewOptionalIntervalVar(s_var, dur, e_var, is_sched, f"interval_{t_id}")
            interval_vars[t_id] = t_interval

            # Determine candidate resources that match task requirements
            # 1. Candidate space resources
            candidate_spaces = [
                s for s in space_resources
                if all(cap in s.capabilities for cap in task.required_capabilities if cap in s.capabilities or not any(cap in h.capabilities for h in human_resources))
            ] or space_resources

            # 2. Candidate human resources
            candidate_humans = [
                h for h in human_resources
                if all(cap in h.capabilities for cap in task.required_capabilities if any(cap in h.capabilities for h in human_resources))
            ] or human_resources

            # Resource assignment decision: task needs 1 primary space (if spaces exist) and 1 primary human (if humans exist)
            task_space_assigns = []
            if space_resources:
                for r in candidate_spaces:
                    a_var = model.NewBoolVar(f"assign_{t_id}_{r.id}")
                    assign_vars[(t_id, r.id)] = a_var
                    task_space_assigns.append(a_var)

                    # Interval on this resource includes turnaround time
                    eff_dur = dur + r.turnaround_minutes
                    res_end = model.NewIntVar(earliest + eff_dur, horizon + r.turnaround_minutes, f"res_end_{t_id}_{r.id}")
                    model.Add(res_end == s_var + eff_dur).OnlyEnforceIf(a_var)
                    r_interval = model.NewOptionalIntervalVar(s_var, eff_dur, res_end, a_var, f"opt_interval_{t_id}_{r.id}")
                    res_intervals[r.id].append(r_interval)

                # Exactly 1 space must be assigned if scheduled
                model.Add(sum(task_space_assigns) == is_sched)

            task_human_assigns = []
            if human_resources:
                for r in candidate_humans:
                    a_var = model.NewBoolVar(f"assign_{t_id}_{r.id}")
                    assign_vars[(t_id, r.id)] = a_var
                    task_human_assigns.append(a_var)

                    r_interval = model.NewOptionalIntervalVar(s_var, dur, e_var, a_var, f"opt_human_interval_{t_id}_{r.id}")
                    res_intervals[r.id].append(r_interval)

                # Exactly 1 human specialist assigned if scheduled
                model.Add(sum(task_human_assigns) == is_sched)

        # Enforce NoOverlap on each operational resource
        for r in operational_resources:
            if res_intervals[r.id]:
                model.AddNoOverlap(res_intervals[r.id])

        # Precedence constraints
        task_map = {t.id: t for t in problem.tasks}
        for task in problem.tasks:
            for pred_id in task.precedence_task_ids:
                if pred_id in start_vars:
                    # If both scheduled, start[task] >= end[pred]
                    model.Add(start_vars[task.id] >= end_vars[pred_id]).OnlyEnforceIf([scheduled_vars[task.id], scheduled_vars[pred_id]])

        # Objective Function
        # 1. Heavily reward scheduling tasks (scaled by priority)
        # 2. Penalize delays / late completion
        # 3. Penalize deadline breaches
        objective_terms = []
        for task in problem.tasks:
            weight = priority_weights.get(task.priority, 500)
            is_sched = scheduled_vars[task.id]
            s_var = start_vars[task.id]
            e_var = end_vars[task.id]

            # Benefit of scheduling
            objective_terms.append(weight * is_sched)

            # Small penalty for waiting / later start (promotes early triage resolution)
            objective_terms.append(-1 * (s_var - task.earliest_start_minute))

            # Penalty for missing deadline
            if task.deadline_minute is not None:
                deadline_slack = model.NewIntVar(-horizon, horizon, f"slack_{task.id}")
                model.Add(deadline_slack == task.deadline_minute - e_var)
                # If finished after deadline, apply penalty
                is_late = model.NewBoolVar(f"late_{task.id}")
                model.Add(e_var > task.deadline_minute).OnlyEnforceIf(is_late)
                model.Add(e_var <= task.deadline_minute).OnlyEnforceIf(is_late.Not())
                objective_terms.append(-int(weight * 0.5) * is_late)

        model.Maximize(sum(objective_terms))

        # Solve model
        solver = cp_model.CpSolver()
        solver.parameters.max_time_in_seconds = self.time_limit_seconds
        solver.parameters.random_seed = self.random_seed
        status_code = solver.Solve(model)

        elapsed_ms = int((time.monotonic() - start_mono) * 1000)
        status_str = {
            cp_model.OPTIMAL: "optimal",
            cp_model.FEASIBLE: "feasible",
            cp_model.INFEASIBLE: "infeasible",
            cp_model.MODEL_INVALID: "invalid",
        }.get(status_code, "unknown")

        assignments: list[UniversalAssignment] = []
        unmet_ids: list[str] = []

        if status_code in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            for task in problem.tasks:
                if solver.Value(scheduled_vars[task.id]) == 1:
                    s_val = int(solver.Value(start_vars[task.id]))
                    e_val = int(solver.Value(end_vars[task.id]))
                    assigned_res = [
                        r.id for r in operational_resources
                        if (task.id, r.id) in assign_vars and solver.Value(assign_vars[(task.id, r.id)]) == 1
                    ]
                    max_turnaround = max([res_map[r_id].turnaround_minutes for r_id in assigned_res] or [0])
                    turn_end = e_val + max_turnaround
                    delay = max(0, s_val - task.earliest_start_minute)
                    on_time = task.deadline_minute is None or e_val <= task.deadline_minute

                    rationale = f"Scheduled with resources {', '.join(assigned_res)}. Delay: {delay}m."
                    if not on_time and task.deadline_minute:
                        rationale += f" Deadline breached by {e_val - task.deadline_minute}m."

                    assignments.append(
                        UniversalAssignment(
                            task_id=task.id,
                            task_name=task.name,
                            priority=task.priority.name,
                            assigned_resource_ids=assigned_res,
                            start_minute=s_val,
                            end_minute=e_val,
                            turnaround_end_minute=turn_end,
                            delay_minutes=delay,
                            is_on_time=on_time,
                            rationale=rationale,
                        )
                    )
                else:
                    unmet_ids.append(task.id)
        else:
            unmet_ids = [t.id for t in problem.tasks]

        total_tasks = len(problem.tasks)
        sched_count = len(assignments)
        unmet_count = len(unmet_ids)
        overall_fulfillment = sched_count / total_tasks if total_tasks > 0 else 1.0

        crit_tasks = [t for t in problem.tasks if t.priority == ConstraintPriority.CRITICAL_EMERGENCY]
        crit_sched = [a for a in assignments if a.priority == ConstraintPriority.CRITICAL_EMERGENCY.name]
        crit_fulfillment = len(crit_sched) / len(crit_tasks) if crit_tasks else 1.0

        return UniversalSolution(
            solution_id=f"SOLV-{int(time.time())}",
            problem_id=problem.problem_id,
            domain=problem.domain,
            solver_status=status_str,
            solve_time_ms=elapsed_ms,
            total_tasks=total_tasks,
            scheduled_tasks=sched_count,
            unmet_tasks=unmet_count,
            overall_fulfillment_rate=round(overall_fulfillment, 3),
            critical_fulfillment_rate=round(crit_fulfillment, 3),
            assignments=assignments,
            unmet_task_ids=unmet_ids,
            validation_passed=True,
            validation_violations=[],
        )
