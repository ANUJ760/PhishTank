"""Tests for disruption impact analysis and minimal-change schedule recovery."""

from __future__ import annotations

import pytest
from gecompose.api import (
    GeComposeEngine,
    analyze_impact,
    recover_schedule,
    serialize_result,
    to_timetable_grid,
)
from gecompose.exceptions import ValidationError
from gecompose.models import (
    DisruptionEvent,
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
from gecompose.recovery import DisruptionRecoverer, analyze_disruption_impact


@pytest.fixture
def base_problem_and_schedule():
    """Create a 3-session schedule across 2 rooms, 2 teachers, and 2 slots."""
    slots = [
        TimeSlot(id="mon_0900", day="Monday", start_time="09:00", end_time="10:00"),
        TimeSlot(id="mon_1000", day="Monday", start_time="10:00", end_time="11:00"),
    ]
    teachers = [
        Teacher(id="prof_alice", name="Alice", qualifications={"CS", "Math"}),
        Teacher(id="prof_bob", name="Bob", qualifications={"Physics"}),
    ]
    rooms = [
        Room(id="room_101", name="Hall 101", capacity=40),
        Room(id="room_102", name="Hall 102", capacity=30),
        Room(id="room_103", name="Hall 103", capacity=35),
    ]
    sessions = [
        Session(id="cs_intro", title="Intro CS", subject="CS", expected_students=25),
        Session(id="math_intro", title="Intro Math", subject="Math", expected_students=35),
        Session(id="phys_intro", title="Intro Physics", subject="Physics", expected_students=20),
    ]
    problem = SchedulingProblem(
        slots=slots, teachers=teachers, rooms=rooms, sessions=sessions
    )

    # Initial verified schedule:
    # - cs_intro in room_101 at mon_0900 (prof_alice)
    # - phys_intro in room_102 at mon_0900 (prof_bob)
    # - math_intro in room_101 at mon_1000 (prof_alice)
    assignments = [
        ScheduledAssignment(session_id="cs_intro", teacher_id="prof_alice", room_id="room_101", slot_id="mon_0900"),
        ScheduledAssignment(session_id="phys_intro", teacher_id="prof_bob", room_id="room_102", slot_id="mon_0900"),
        ScheduledAssignment(session_id="math_intro", teacher_id="prof_alice", room_id="room_101", slot_id="mon_1000"),
    ]
    return problem, assignments


class TestDisruptionImpactAnalysis:
    """Tests for analyze_disruption_impact."""

    def test_direct_room_disruption_impact(self, base_problem_and_schedule):
        problem, assignments = base_problem_and_schedule
        event = DisruptionEvent(
            id="leak_101",
            resource_type=ResourceType.ROOM,
            resource_id="room_101",
            slot_ids={"mon_0900"},
            reason="Water pipe maintenance",
        )
        report = analyze_disruption_impact(problem, assignments, event)
        assert report.has_impact is True
        assert report.directly_affected_session_ids == ["cs_intro"]
        assert len(report.directly_affected_assignments) == 1
        assert report.directly_affected_assignments[0].session_id == "cs_intro"
        assert set(report.unaffected_session_ids) == {"phys_intro", "math_intro"}

    def test_disruption_via_time_interval(self, base_problem_and_schedule):
        problem, assignments = base_problem_and_schedule
        event = DisruptionEvent(
            id="closure_all_morning",
            resource_type=ResourceType.ROOM,
            resource_id="room_101",
            day="Monday",
            start_time="08:30",
            end_time="11:30",
            reason="Full morning maintenance",
        )
        report = analyze_disruption_impact(problem, assignments, event)
        assert report.has_impact is True
        # Both cs_intro (09:00) and math_intro (10:00) in room_101 are affected
        assert set(report.directly_affected_session_ids) == {"cs_intro", "math_intro"}
        assert report.unaffected_session_ids == ["phys_intro"]

    def test_disruption_with_no_affected_assignments(self, base_problem_and_schedule):
        problem, assignments = base_problem_and_schedule
        event = DisruptionEvent(
            id="closure_unused",
            resource_type=ResourceType.ROOM,
            resource_id="room_102",
            slot_ids={"mon_1000"},  # room_102 is empty at mon_1000
            reason="Deep cleaning",
        )
        report = analyze_disruption_impact(problem, assignments, event)
        assert report.has_impact is False
        assert len(report.directly_affected_session_ids) == 0
        assert len(report.unaffected_session_ids) == 3

    def test_invalid_resource_reference_raises_error(self, base_problem_and_schedule):
        problem, assignments = base_problem_and_schedule
        bad_event = DisruptionEvent(
            id="bad_room",
            resource_type=ResourceType.ROOM,
            resource_id="nonexistent_room",
            slot_ids={"mon_0900"},
        )
        with pytest.raises(ValidationError, match="references unknown room"):
            analyze_disruption_impact(problem, assignments, bad_event)

    def test_invalid_slot_reference_raises_error(self, base_problem_and_schedule):
        problem, assignments = base_problem_and_schedule
        bad_event = DisruptionEvent(
            id="bad_slot",
            resource_type=ResourceType.ROOM,
            resource_id="room_101",
            slot_ids={"ghost_slot"},
        )
        with pytest.raises(ValidationError, match="references unknown slot"):
            analyze_disruption_impact(problem, assignments, bad_event)


class TestMinimalChangeRecovery:
    """Tests for DisruptionRecoverer and minimal-change recovery optimization."""

    def test_recover_by_moving_single_session_to_open_room(self, base_problem_and_schedule):
        problem, assignments = base_problem_and_schedule
        # room_101 closed at mon_0900.
        # cs_intro (expected: 25) can move to room_102 at mon_1000 (capacity: 30, free).
        # Unaffected sessions should remain strictly intact!
        event = DisruptionEvent(
            id="leak_101",
            resource_type=ResourceType.ROOM,
            resource_id="room_101",
            slot_ids={"mon_0900"},
            reason="Pipe leak in 101",
        )
        recoverer = DisruptionRecoverer()
        result = recoverer.recover(problem, assignments, event)

        assert result.is_success is True
        assert result.status in (SolverStatus.OPTIMAL, SolverStatus.FEASIBLE)
        assert result.validation_passed is True
        assert len(result.violations) == 0
        assert len(result.recovered_assignments) == 3

        # Directly affected: cs_intro
        assert result.directly_affected_session_ids == ["cs_intro"]
        assert "cs_intro" in result.moved_session_ids

        # Unaffected sessions MUST NOT MOVE
        assert "phys_intro" in result.unaffected_session_ids
        assert "math_intro" in result.unaffected_session_ids

        # Inspect cs_intro's new assignment
        new_cs = next(a for a in result.recovered_assignments if a.session_id == "cs_intro")
        assert new_cs.room_id != "room_101" or new_cs.slot_id != "mon_0900"
        # Room 101 at mon_0900 must not host any session
        for a in result.recovered_assignments:
            assert not (a.room_id == "room_101" and a.slot_id == "mon_0900")

        # Verify change log
        assert len(result.changes) >= 1
        cs_change = next(c for c in result.changes if c.session_id == "cs_intro")
        assert cs_change.original_assignment.room_id == "room_101"
        assert cs_change.original_assignment.slot_id == "mon_0900"

    def test_cascade_relocation_when_necessary(self):
        # Only 2 rooms, tightly packed schedule
        slots = [
            TimeSlot(id="mon_0900", day="Monday", start_time="09:00", end_time="10:00"),
            TimeSlot(id="mon_1000", day="Monday", start_time="10:00", end_time="11:00"),
        ]
        teachers = [
            Teacher(id="prof_alice", name="Alice", qualifications={"CS", "Math"}),
            Teacher(id="prof_bob", name="Bob", qualifications={"Physics"}),
        ]
        rooms = [
            Room(id="room_101", name="Hall 101", capacity=40),
            Room(id="room_102", name="Hall 102", capacity=30),
        ]
        sessions = [
            Session(id="cs_intro", title="Intro CS", subject="CS", expected_students=25),
            Session(id="math_intro", title="Intro Math", subject="Math", expected_students=35),
            Session(id="phys_intro", title="Intro Physics", subject="Physics", expected_students=20),
        ]
        problem = SchedulingProblem(slots=slots, teachers=teachers, rooms=rooms, sessions=sessions)
        assignments = [
            ScheduledAssignment(session_id="cs_intro", teacher_id="prof_alice", room_id="room_101", slot_id="mon_0900"),
            ScheduledAssignment(session_id="phys_intro", teacher_id="prof_bob", room_id="room_102", slot_id="mon_0900"),
            ScheduledAssignment(session_id="math_intro", teacher_id="prof_alice", room_id="room_101", slot_id="mon_1000"),
        ]
        # Room 101 closes at 09:00. cs_intro must take room_102 at 09:00 because prof_alice is busy at 10:00.
        # This forces phys_intro to be displaced to 10:00 (cascade relocation).
        event = DisruptionEvent(
            id="pipe_burst",
            resource_type=ResourceType.ROOM,
            resource_id="room_101",
            slot_ids={"mon_0900"},
        )
        result = recover_schedule(problem, assignments, event)
        assert result.is_success is True
        assert result.directly_affected_session_ids == ["cs_intro"]
        assert set(result.moved_session_ids) == {"cs_intro", "phys_intro"}
        assert result.unaffected_session_ids == ["math_intro"]
        assert result.statistics["displaced_unaffected"] == 1

        # Check cascade explanation in change record
        phys_change = next(c for c in result.changes if c.session_id == "phys_intro")
        assert "cascade" in phys_change.reason.lower()

    def test_unaffected_disruption_returns_original_schedule(self, base_problem_and_schedule):
        problem, assignments = base_problem_and_schedule
        event = DisruptionEvent(
            id="unused_room_closure",
            resource_type=ResourceType.ROOM,
            resource_id="room_102",
            slot_ids={"mon_1000"},  # room_102 is already free here
        )
        engine = GeComposeEngine()
        result = engine.recover_schedule(problem, assignments, event)

        assert result.is_success is True
        assert result.total_changes == 0
        assert len(result.moved_session_ids) == 0
        assert set(result.unaffected_session_ids) == {"cs_intro", "phys_intro", "math_intro"}
        assert result.total_penalty == 0

    def test_impossible_recovery_honestly_reports_infeasible(self):
        # 1 slot, 1 room, 1 session. Room closes. No other room exists.
        slot = TimeSlot(id="s1", day="Mon", start_time="09:00", end_time="10:00")
        teacher = Teacher(id="t1", name="Alice")
        room = Room(id="r1", name="Hall", capacity=30)
        session = Session(id="c1", title="Class", expected_students=20)
        problem = SchedulingProblem(
            slots=[slot], teachers=[teacher], rooms=[room], sessions=[session]
        )
        assignments = [ScheduledAssignment(session_id="c1", teacher_id="t1", room_id="r1", slot_id="s1")]

        event = DisruptionEvent(
            id="fire_alarm",
            resource_type=ResourceType.ROOM,
            resource_id="r1",
            slot_ids={"s1"},
            reason="Building evacuation",
        )
        result = recover_schedule(problem, assignments, event)

        assert result.status == SolverStatus.INFEASIBLE
        assert result.is_success is False
        assert len(result.recovered_assignments) == 0
        assert "infeasible" in result.message.lower()

    def test_impossible_recovery_due_to_capacity(self):
        # Room 101 (cap 50) closes. Room 102 (cap 20) is available, but class has 40 students!
        slot = TimeSlot(id="s1", day="Mon", start_time="09:00", end_time="10:00")
        teacher = Teacher(id="t1", name="Alice")
        rooms = [
            Room(id="r101", name="Big Room", capacity=50),
            Room(id="r102", name="Small Room", capacity=20),
        ]
        session = Session(id="big_class", title="Big Lecture", expected_students=40)
        problem = SchedulingProblem(
            slots=[slot], teachers=[teacher], rooms=rooms, sessions=[session]
        )
        assignments = [ScheduledAssignment(session_id="big_class", teacher_id="t1", room_id="r101", slot_id="s1")]

        event = DisruptionEvent(
            id="r101_flood",
            resource_type=ResourceType.ROOM,
            resource_id="r101",
            slot_ids={"s1"},
        )
        result = recover_schedule(problem, assignments, event)
        assert result.status == SolverStatus.INFEASIBLE
        assert result.is_success is False

    def test_engine_facade_and_serialization(self, base_problem_and_schedule):
        problem, assignments = base_problem_and_schedule
        event = DisruptionEvent(
            id="teacher_sick",
            resource_type=ResourceType.TEACHER,
            resource_id="prof_bob",
            slot_ids={"mon_0900", "mon_1000"},
            reason="Sudden flu for full day",
        )
        engine = GeComposeEngine()
        impact = engine.analyze_disruption_impact(problem, assignments, event)
        assert impact.has_impact is True
        assert impact.directly_affected_session_ids == ["phys_intro"]

        # phys_intro requires "Physics", prof_alice lacks "Physics", and prof_bob is out all day.
        # Recovery is mathematically impossible!
        recovery = engine.recover_schedule(problem, assignments, event)
        assert recovery.status == SolverStatus.INFEASIBLE
        assert recovery.is_success is False

        # Test serialize_result
        dumped_impact = engine.serialize_result(impact)
        assert dumped_impact["has_impact"] is True
        assert dumped_impact["disruption"]["id"] == "teacher_sick"

        dumped_recovery = engine.serialize_result(recovery)
        assert dumped_recovery["status"] == "INFEASIBLE"
        assert dumped_recovery["is_success"] is False

    def test_to_timetable_grid_with_recovery_result(self, base_problem_and_schedule):
        problem, assignments = base_problem_and_schedule
        event = DisruptionEvent(
            id="closure_unused",
            resource_type=ResourceType.ROOM,
            resource_id="room_102",
            slot_ids={"mon_1000"},
        )
        recovery = recover_schedule(problem, assignments, event)
        grid = to_timetable_grid(recovery, problem)
        assert len(grid) >= 1
        all_grid_assignments = [a for cell in grid.values() for a in cell]
        assert len(all_grid_assignments) == 3

    def test_timeout_budget_honored(self, base_problem_and_schedule):
        problem, assignments = base_problem_and_schedule
        event = DisruptionEvent(
            id="leak_101",
            resource_type=ResourceType.ROOM,
            resource_id="room_101",
            slot_ids={"mon_0900"},
        )
        policy = RecoveryPolicy(time_limit_seconds=0.0001)
        # Fast execution, should return either a solution if immediate or TIMEOUT
        result = recover_schedule(problem, assignments, event, policy=policy)
        assert result.status in (SolverStatus.OPTIMAL, SolverStatus.FEASIBLE, SolverStatus.TIMEOUT)
