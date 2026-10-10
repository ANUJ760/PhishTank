"""Unit and integration tests for the CP-SAT scheduling engine."""

import pytest
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
from gecompose.solver import CPSATScheduler, solve_schedule


@pytest.fixture
def scheduler():
    return CPSATScheduler(time_limit_seconds=5.0)


class TestCPSATSolverSuccess:
    def test_feasible_schedule_satisfies_all_constraints(self, scheduler):
        """Test that a feasible scheduling problem produces a 100% valid schedule."""
        problem = SchedulingProblem(
            teachers=[
                Teacher(id="t_rao", name="Prof. Rao", qualifications={"Databases", "Algorithms"}),
                Teacher(id="t_mehta", name="Prof. Mehta", qualifications={"AI", "Algorithms"}),
            ],
            rooms=[
                Room(id="r_lab", name="Lab 101", capacity=40),
                Room(id="r_hall", name="Auditorium", capacity=120),
            ],
            slots=[
                TimeSlot(id="mon_09", day="Monday", start_time="09:00", end_time="10:00"),
                TimeSlot(id="mon_10", day="Monday", start_time="10:00", end_time="11:00"),
                TimeSlot(id="tue_09", day="Tuesday", start_time="09:00", end_time="10:00"),
            ],
            sessions=[
                Session(id="sess_db", subject="Databases", expected_students=35),
                Session(id="sess_ai", subject="AI", expected_students=100),
                Session(id="sess_algo", subject="Algorithms", expected_students=30),
            ],
        )

        result = scheduler.solve(problem)

        assert result.status in (SolverStatus.OPTIMAL, SolverStatus.FEASIBLE)
        assert result.validation_passed is True
        assert len(result.assignments) == 3

        # Verify assignments match hard constraints
        assigned_map = {a.session_id: a for a in result.assignments}

        # Databases must be taught by Prof. Rao in a room with capacity >= 35
        db_assignment = assigned_map["sess_db"]
        assert db_assignment.teacher_id == "t_rao"

        # AI session (100 students) MUST be in the Auditorium (r_hall)
        ai_assignment = assigned_map["sess_ai"]
        assert ai_assignment.teacher_id == "t_mehta"
        assert ai_assignment.room_id == "r_hall"

    def test_pinned_entities_respected(self, scheduler):
        """Test that pinned teacher, room, and slot constraints are strictly enforced."""
        problem = SchedulingProblem(
            teachers=[
                Teacher(id="t1", name="Prof. A", qualifications={"Math"}),
                Teacher(id="t2", name="Prof. B", qualifications={"Math"}),
            ],
            rooms=[
                Room(id="r1", name="Room 1", capacity=50),
                Room(id="r2", name="Room 2", capacity=50),
            ],
            slots=[
                TimeSlot(id="s1", day="Monday", start_time="09:00", end_time="10:00"),
                TimeSlot(id="s2", day="Monday", start_time="10:00", end_time="11:00"),
            ],
            sessions=[
                Session(
                    id="pinned_sess",
                    subject="Math",
                    pinned_teacher_id="t2",
                    pinned_room_id="r2",
                    pinned_slot_id="s1",
                ),
                Session(id="other_sess", subject="Math"),
            ],
        )

        result = scheduler.solve(problem)
        assert result.status in (SolverStatus.OPTIMAL, SolverStatus.FEASIBLE)
        assert result.validation_passed is True

        assigned_map = {a.session_id: a for a in result.assignments}
        pinned = assigned_map["pinned_sess"]
        assert pinned.teacher_id == "t2"
        assert pinned.room_id == "r2"
        assert pinned.slot_id == "s1"

        other = assigned_map["other_sess"]
        # other cannot use (t2, s1) or (r2, s1)
        assert not (other.teacher_id == "t2" and other.slot_id == "s1")
        assert not (other.room_id == "r2" and other.slot_id == "s1")

    def test_teacher_unavailability_respected(self, scheduler):
        """Test that teachers are never placed into their unavailable slots."""
        problem = SchedulingProblem(
            teachers=[
                Teacher(
                    id="t1",
                    name="Prof. Rao",
                    qualifications={"Math"},
                    unavailable_slots={"s1"},  # unavailable at 9am
                ),
            ],
            rooms=[Room(id="r1", name="Room 1", capacity=50)],
            slots=[
                TimeSlot(id="s1", day="Monday", start_time="09:00", end_time="10:00"),
                TimeSlot(id="s2", day="Monday", start_time="10:00", end_time="11:00"),
            ],
            sessions=[Session(id="c1", subject="Math")],
        )

        result = scheduler.solve(problem)
        assert result.status in (SolverStatus.OPTIMAL, SolverStatus.FEASIBLE)
        assert result.assignments[0].slot_id == "s2"


class TestCPSATSolverInfeasibility:
    def test_infeasible_overlapping_teacher_conflict(self, scheduler):
        """Two sessions pinned to the same teacher at the exact same slot must return INFEASIBLE."""
        problem = SchedulingProblem(
            teachers=[Teacher(id="t1", name="Prof. Rao", qualifications={"Math"})],
            rooms=[
                Room(id="r1", name="Room 1", capacity=50),
                Room(id="r2", name="Room 2", capacity=50),
            ],
            slots=[TimeSlot(id="s1", day="Monday", start_time="09:00", end_time="10:00")],
            sessions=[
                Session(id="c1", subject="Math", pinned_teacher_id="t1", pinned_slot_id="s1"),
                Session(id="c2", subject="Math", pinned_teacher_id="t1", pinned_slot_id="s1"),
            ],
        )

        result = scheduler.solve(problem)
        assert result.status == SolverStatus.INFEASIBLE
        assert result.validation_passed is False
        assert len(result.assignments) == 0

    def test_infeasible_overlapping_room_conflict(self, scheduler):
        """Two sessions pinned to the same room at overlapping slots must return INFEASIBLE."""
        problem = SchedulingProblem(
            teachers=[
                Teacher(id="t1", name="Prof. A", qualifications={"Math"}),
                Teacher(id="t2", name="Prof. B", qualifications={"Math"}),
            ],
            rooms=[Room(id="r1", name="Room 1", capacity=50)],
            slots=[
                TimeSlot(id="s1", day="Monday", start_time="09:00", end_time="10:00"),
                TimeSlot(id="s_overlap", day="Monday", start_time="09:30", end_time="10:30"),
            ],
            sessions=[
                Session(id="c1", subject="Math", pinned_room_id="r1", pinned_slot_id="s1"),
                Session(id="c2", subject="Math", pinned_room_id="r1", pinned_slot_id="s_overlap"),
            ],
        )

        result = scheduler.solve(problem)
        assert result.status == SolverStatus.INFEASIBLE
        assert result.validation_passed is False
        assert len(result.assignments) == 0

    def test_infeasible_no_qualified_teacher(self, scheduler):
        """A session with a required qualification no teacher holds must return INFEASIBLE."""
        problem = SchedulingProblem(
            teachers=[Teacher(id="t1", name="Prof. Rao", qualifications={"Math"})],
            rooms=[Room(id="r1", name="Room 1", capacity=50)],
            slots=[TimeSlot(id="s1", day="Monday", start_time="09:00", end_time="10:00")],
            sessions=[Session(id="c1", subject="Quantum Computing")],
        )

        result = scheduler.solve(problem)
        assert result.status == SolverStatus.INFEASIBLE
        assert result.validation_passed is False
        assert len(result.assignments) == 0

    def test_infeasible_insufficient_room_capacity(self, scheduler):
        """A session with 100 students when max room capacity is 50 must return INFEASIBLE."""
        problem = SchedulingProblem(
            teachers=[Teacher(id="t1", name="Prof. Rao", qualifications={"Math"})],
            rooms=[Room(id="r1", name="Room 1", capacity=50)],
            slots=[TimeSlot(id="s1", day="Monday", start_time="09:00", end_time="10:00")],
            sessions=[Session(id="c1", subject="Math", expected_students=100)],
        )

        result = scheduler.solve(problem)
        assert result.status == SolverStatus.INFEASIBLE
        assert result.validation_passed is False
        assert len(result.assignments) == 0

    def test_infeasible_teacher_unavailable_at_pinned_slot(self, scheduler):
        """If a teacher is pinned to a slot where they are unavailable, return INFEASIBLE."""
        problem = SchedulingProblem(
            teachers=[
                Teacher(id="t1", name="Prof. Rao", qualifications={"Math"}, unavailable_slots={"s1"})
            ],
            rooms=[Room(id="r1", name="Room 1", capacity=50)],
            slots=[TimeSlot(id="s1", day="Monday", start_time="09:00", end_time="10:00")],
            sessions=[
                Session(id="c1", subject="Math", pinned_teacher_id="t1", pinned_slot_id="s1")
            ],
        )

        result = scheduler.solve(problem)
        assert result.status == SolverStatus.INFEASIBLE
        assert result.validation_passed is False
        assert len(result.assignments) == 0

    def test_infeasible_pigeonhole_bottleneck(self, scheduler):
        """3 sessions requiring 3 rooms at the same time slot with only 2 rooms available."""
        problem = SchedulingProblem(
            teachers=[
                Teacher(id="t1", name="Prof. 1", qualifications={"Math"}),
                Teacher(id="t2", name="Prof. 2", qualifications={"Math"}),
                Teacher(id="t3", name="Prof. 3", qualifications={"Math"}),
            ],
            rooms=[
                Room(id="r1", name="Room 1", capacity=50),
                Room(id="r2", name="Room 2", capacity=50),
            ],
            slots=[
                TimeSlot(id="s1", day="Monday", start_time="09:00", end_time="10:00"),
            ],
            sessions=[
                Session(id="c1", subject="Math"),
                Session(id="c2", subject="Math"),
                Session(id="c3", subject="Math"),
            ],
        )

        result = scheduler.solve(problem)
        assert result.status == SolverStatus.INFEASIBLE
        assert result.validation_passed is False
        assert len(result.assignments) == 0
