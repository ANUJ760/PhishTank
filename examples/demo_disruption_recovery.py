#!/usr/bin/env python3
"""GeCompose Phase 4 - Disruption Impact Analysis & Minimal-Change Recovery Demo.

Demonstrates Campus Operations Intelligence:
1. Generating an approved baseline schedule.
2. Simulating a real-world disruption (e.g. computer lab closure due to maintenance).
3. Analyzing direct impact (identifying affected vs unaffected sessions).
4. Computing a minimal-change recovery schedule using CP-SAT optimization.
5. Displaying itemized changes, change penalties, and before/after timetable grids.
6. Demonstrating honest handling of impossible recovery scenarios.

Usage:
    python examples/demo_disruption_recovery.py
"""

from __future__ import annotations

from gecompose import (
    DisruptionEvent,
    GeComposeEngine,
    RecoveryPolicy,
    ResourceType,
    Room,
    Session,
    Teacher,
    TimeSlot,
    SchedulingProblem,
)


def run_demo() -> None:
    print("=" * 75)
    print(" GeCompose: Disruption Impact Analysis & Minimal-Change Recovery")
    print("=" * 75)

    engine = GeComposeEngine()

    # -------------------------------------------------------------------------
    # 1. Baseline Schedule Generation
    # -------------------------------------------------------------------------
    print("\n--- [1] Generating Approved Baseline Schedule ---")
    slots = [
        TimeSlot(id="mon_0900", day="Monday", start_time="09:00", end_time="10:00"),
        TimeSlot(id="mon_1000", day="Monday", start_time="10:00", end_time="11:00"),
    ]
    teachers = [
        Teacher(id="prof_turing", name="Alan Turing", qualifications={"CS", "Math"}),
        Teacher(id="prof_curie", name="Marie Curie", qualifications={"Physics"}),
    ]
    rooms = [
        Room(id="lab_101", name="Computing Lab 101", capacity=40),
        Room(id="hall_201", name="Lecture Hall 201", capacity=50),
        Room(id="seminar_301", name="Seminar Room 301", capacity=30),
    ]
    sessions = [
        Session(id="cs_algorithms", title="Algorithms Lab", subject="CS", expected_students=35),
        Session(id="math_calculus", title="Calculus Lecture", subject="Math", expected_students=30),
        Session(id="phys_mechanics", title="Mechanics Seminar", subject="Physics", expected_students=25),
    ]

    problem = SchedulingProblem(
        slots=slots, teachers=teachers, rooms=rooms, sessions=sessions
    )

    baseline_res = engine.schedule(problem)
    assert baseline_res.is_success, "Baseline schedule must be feasible"
    print(f"Baseline Schedule Status: {baseline_res.status.value}")
    print(f"Total Sessions Scheduled: {len(baseline_res.assignments)}")

    grid_baseline = engine.to_timetable_grid(baseline_res, problem)
    print("\nApproved Baseline Timetable:")
    for (day, slot_id), assigns in sorted(grid_baseline.items()):
        for a in assigns:
            print(f"  [{day} | {slot_id}] {a.session_id:<16} -> Room: {a.room_id:<14} | Teacher: {a.teacher_id}")

    # -------------------------------------------------------------------------
    # 2. Campus Disruption Event: Lab 101 Closes at 09:00
    # -------------------------------------------------------------------------
    print("\n--- [2] Disruption Event: Emergency Closure ---")
    lab_disruption = DisruptionEvent(
        id="incident_leak_lab101",
        resource_type=ResourceType.ROOM,
        resource_id="lab_101",
        slot_ids={"mon_0900"},
        reason="Overhead water pipe leakage required immediate facility closure.",
    )
    print(f"Event ID:      {lab_disruption.id}")
    print(f"Disrupted:     {lab_disruption.resource_type.value.upper()} '{lab_disruption.resource_id}'")
    print(f"Time Window:   Slots {lab_disruption.slot_ids}")
    print(f"Reason:        {lab_disruption.reason}")

    # -------------------------------------------------------------------------
    # 3. Disruption Impact Analysis
    # -------------------------------------------------------------------------
    print("\n--- [3] Impact Analysis Report ---")
    impact = engine.analyze_disruption_impact(problem, baseline_res.assignments, lab_disruption)
    print(f"Direct Impact Detected: {impact.has_impact}")
    print(f"Directly Affected Sessions: {impact.directly_affected_session_ids}")
    print(f"Unaffected Active Sessions: {impact.unaffected_session_ids}")

    # -------------------------------------------------------------------------
    # 4. Minimal-Change Recovery Optimization
    # -------------------------------------------------------------------------
    print("\n--- [4] Solving Minimal-Change Recovery Schedule ---")
    policy = RecoveryPolicy(
        room_change_penalty=1,
        slot_change_penalty=3,
        teacher_change_penalty=10,
        unaffected_displacement_penalty=25,
    )
    recovery = engine.recover_schedule(
        problem, baseline_res.assignments, lab_disruption, policy=policy
    )

    print(f"Recovery Status:     {recovery.status.value}")
    print(f"Independent Check:   Passed = {recovery.validation_passed}")
    print(f"Solve Time:          {recovery.wall_time_seconds:.4f}s")
    print(f"Total Change Score:  {recovery.total_penalty}")
    print(f"Total Modifications: {recovery.total_changes}")

    print("\nItemized Schedule Modifications:")
    for change in recovery.changes:
        print(f"  * Session '{change.session_id}':")
        print(f"      Original: Room={change.original_assignment.room_id}, Slot={change.original_assignment.slot_id}")
        print(f"      Recovered: Room={change.new_assignment.room_id}, Slot={change.new_assignment.slot_id}")
        print(f"      Reason:   {change.reason}")

    print(f"\nProtected Unaffected Sessions (Zero Changes):")
    for s_id in recovery.unaffected_session_ids:
        print(f"  * {s_id} (Remained in original room and time slot)")

    grid_recovered = engine.to_timetable_grid(recovery, problem)
    print("\nRecovered Timetable Grid:")
    for (day, slot_id), assigns in sorted(grid_recovered.items()):
        for a in assigns:
            print(f"  [{day} | {slot_id}] {a.session_id:<16} -> Room: {a.room_id:<14} | Teacher: {a.teacher_id}")

    # -------------------------------------------------------------------------
    # 5. Impossible Disruption Scenario (Honest Reporting)
    # -------------------------------------------------------------------------
    print("\n--- [5] Demonstrating Impossible Recovery (Honest Infeasibility) ---")
    # All qualified teachers for Physics are unavailable
    impossible_event = DisruptionEvent(
        id="all_teachers_strike",
        resource_type=ResourceType.TEACHER,
        resource_id="prof_curie",
        slot_ids={"mon_0900", "mon_1000"},
        reason="Mandatory full-day research symposium off-campus.",
    )
    impossible_recovery = engine.recover_schedule(
        problem, baseline_res.assignments, impossible_event
    )
    print(f"Impossible Event: Prof. Curie unavailable all day (sole Physics instructor)")
    print(f"Recovery Status:  {impossible_recovery.status.value}")
    print(f"Success Flag:     {impossible_recovery.is_success}")
    print(f"Solver Message:   {impossible_recovery.message}")

    print("\n" + "=" * 75)
    print(" GeCompose Phase 4 Demo Completed Successfully!")
    print("=" * 75)


if __name__ == "__main__":
    run_demo()
