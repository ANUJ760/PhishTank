#!/usr/bin/env python3
"""GeCompose Phase 3 - End-to-End Workflow Demonstration.

This executable example demonstrates the complete deterministic workflow:
1. Building a scheduling problem with teachers, rooms, slots, and sessions.
2. Solving a feasible problem using GeComposeEngine.
3. Transforming flat assignments into a structured 2D timetable grid.
4. Intentionally introducing a conflict to demonstrate conflict diagnosis (MUS core).
5. Automatically searching for and verifying relaxed alternative schedules.
6. Serializing results to JSON-ready dicts for downstream consumers.

Usage:
    python examples/demo_workflow.py
"""

from __future__ import annotations

import json
from gecompose import (
    GeComposeEngine,
    RelaxationPolicy,
    Room,
    Session,
    SolverStatus,
    Teacher,
    TimeSlot,
    SchedulingProblem,
)


def run_demo() -> None:
    print("=" * 70)
    print(" GeCompose: Deterministic OR-Tools CP-SAT Scheduling Engine Demo")
    print("=" * 70)

    engine = GeComposeEngine(time_limit_seconds=5.0)

    # -------------------------------------------------------------------------
    # Part 1: Solving a Feasible Scheduling Problem
    # -------------------------------------------------------------------------
    print("\n--- [1] Solving a Feasible Schedule ---")

    slots = [
        TimeSlot(id="mon_0900", day="Monday", start_time="09:00", end_time="10:00"),
        TimeSlot(id="mon_1000", day="Monday", start_time="10:00", end_time="11:00"),
        TimeSlot(id="tue_0900", day="Tuesday", start_time="09:00", end_time="10:00"),
    ]
    teachers = [
        Teacher(id="prof_turing", name="Alan Turing", qualifications={"CS", "Math"}),
        Teacher(id="prof_curie", name="Marie Curie", qualifications={"Physics", "Chemistry"}),
    ]
    rooms = [
        Room(id="room_101", name="Hall 101", capacity=50),
        Room(id="lab_201", name="Computing Lab", capacity=30),
    ]
    sessions = [
        Session(id="cs_intro", title="Algorithms & Data Structures", subject="CS", expected_students=25),
        Session(id="phys_intro", title="Mechanics & Waves", subject="Physics", expected_students=45),
        Session(id="math_seminar", title="Discrete Mathematics", subject="Math", expected_students=20),
    ]

    feasible_problem = SchedulingProblem(
        slots=slots, teachers=teachers, rooms=rooms, sessions=sessions
    )

    result = engine.schedule(feasible_problem)
    print(f"Status: {result.status.value}")
    print(f"Independent Verification Passed: {result.validation_passed}")
    print(f"Solve Wall Time: {result.wall_time_seconds:.4f}s")
    print(f"Total Assignments: {len(result.assignments)}")

    # Generate and display Timetable Grid
    grid = engine.to_timetable_grid(result, feasible_problem)
    print("\nFormatted Timetable Grid:")
    for (day, slot_id), assignments in sorted(grid.items()):
        for a in assignments:
            print(f"  [{day} | {slot_id}] -> Session: {a.session_id} | Teacher: {a.teacher_id} | Room: {a.room_id}")

    # -------------------------------------------------------------------------
    # Part 2: Infeasible Problem, Conflict Diagnosis, and Alternatives
    # -------------------------------------------------------------------------
    print("\n--- [2] Infeasible Schedule & Conflict Diagnosis ---")

    # Introduce a conflict: Two sessions forced onto the same teacher at the same slot
    conflicting_sessions = [
        Session(
            id="cs_conflict_1",
            title="Advanced Algorithms",
            subject="CS",
            pinned_teacher_id="prof_turing",
            pinned_slot_id="mon_0900",
        ),
        Session(
            id="cs_conflict_2",
            title="Cryptography",
            subject="CS",
            pinned_teacher_id="prof_turing",
            pinned_slot_id="mon_0900",
        ),
    ]
    infeasible_problem = SchedulingProblem(
        slots=slots,
        teachers=teachers,
        rooms=rooms,
        sessions=conflicting_sessions,
    )

    infeasible_result = engine.schedule(infeasible_problem)
    print(f"Initial Solve Status: {infeasible_result.status.value}")
    print(f"Solve Succeeded: {infeasible_result.is_success}")

    # Diagnose the conflict core
    print("\nDiagnosing Unsatisfiable Core (MUS)...")
    diagnosis = engine.diagnose(infeasible_problem)
    print(f"Diagnosis Status: {diagnosis.status.value}")
    print(f"Proven Infeasible: {diagnosis.is_infeasible}")
    print(f"Minimal Core: {diagnosis.is_minimal}")
    print(f"Conflicting Constraints: {len(diagnosis.conflicting_constraints)}")
    for cc in diagnosis.conflicting_constraints:
        print(f"  * [{cc.constraint_type.value}] {cc.description}")
    if diagnosis.explanation:
        print(f"Explanation: {diagnosis.explanation}")

    # Find verified alternatives
    print("\n--- [3] Generating Solver-Verified Alternative Schedules ---")
    policy = RelaxationPolicy(
        allow_slot_relaxation=True,
        allow_teacher_relaxation=False,
        max_alternatives=2,
    )
    alternatives = engine.find_alternatives(infeasible_problem, policy=policy)
    print(f"Alternative Search Status: {alternatives.status.value}")
    print(f"Found Alternatives: {len(alternatives.alternatives)}")

    for alt in alternatives.alternatives:
        print(f"\nAlternative #{alt.alternative_id} (Penalty: {alt.penalty_score}, Verified: {alt.validation_passed}):")
        for req in alt.relaxed_requirements:
            print(f"  Relaxed: {req.description}")
        for a in alt.assignments:
            print(f"  Assignment: {a.session_id} -> Teacher: {a.teacher_id}, Room: {a.room_id}, Slot: {a.slot_id}")

    # -------------------------------------------------------------------------
    # Part 3: Serialization
    # -------------------------------------------------------------------------
    print("\n--- [4] JSON Serialization ---")
    serialized = engine.serialize_result(alternatives)
    json_output = json.dumps(serialized, indent=2)
    print(f"Serialized AlternativeSearchResult (first 250 chars):\n{json_output[:250]}...\n")

    print("=" * 70)
    print(" GeCompose Phase 3 Demo Completed Successfully!")
    print("=" * 70)


if __name__ == "__main__":
    run_demo()
