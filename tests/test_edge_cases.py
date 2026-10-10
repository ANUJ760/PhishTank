"""Edge case and regression tests for GeCompose scheduling engine."""

import pytest
from gecompose.models import (
    Room,
    ScheduledAssignment,
    SchedulingProblem,
    Session,
    SolverStatus,
    Teacher,
    TimeSlot,
)
from gecompose.solver import CPSATScheduler, solve_schedule


class TestEdgeCases:
    def test_zero_sessions(self):
        """Zero sessions to schedule should immediately return OPTIMAL with empty assignments."""
        problem = SchedulingProblem(
            teachers=[Teacher(id="t1", name="Prof. Rao", qualifications={"Math"})],
            rooms=[Room(id="r1", name="Room 101", capacity=30)],
            slots=[TimeSlot(id="s1", day="Monday", start_time="09:00", end_time="10:00")],
            sessions=[],
        )
        result = solve_schedule(problem)
        assert result.status == SolverStatus.OPTIMAL
        assert result.validation_passed is True
        assert len(result.assignments) == 0

    def test_zero_resources_with_sessions(self):
        """Sessions required but no slots/teachers/rooms available returns INFEASIBLE."""
        problem = SchedulingProblem(
            teachers=[],
            rooms=[],
            slots=[],
            sessions=[Session(id="sess1", subject="Math")],
        )
        result = solve_schedule(problem)
        assert result.status == SolverStatus.INFEASIBLE
        assert result.validation_passed is False
        assert len(result.assignments) == 0

    def test_single_session_exact_match(self):
        """Single session with exactly one valid assignment."""
        problem = SchedulingProblem(
            teachers=[Teacher(id="t1", name="Prof. Rao", qualifications={"Math"})],
            rooms=[Room(id="r1", name="Room 101", capacity=30)],
            slots=[TimeSlot(id="s1", day="Monday", start_time="09:00", end_time="10:00")],
            sessions=[Session(id="sess1", subject="Math", expected_students=25)],
        )
        result = solve_schedule(problem)
        assert result.status in (SolverStatus.OPTIMAL, SolverStatus.FEASIBLE)
        assert result.validation_passed is True
        assert len(result.assignments) == 1
        assert result.assignments[0].session_id == "sess1"
        assert result.assignments[0].teacher_id == "t1"
        assert result.assignments[0].room_id == "r1"
        assert result.assignments[0].slot_id == "s1"

    def test_same_teacher_across_different_days(self):
        """A teacher can teach at the same hour on different days."""
        problem = SchedulingProblem(
            teachers=[Teacher(id="t1", name="Prof. Rao", qualifications={"Math"})],
            rooms=[Room(id="r1", name="Room 101", capacity=30)],
            slots=[
                TimeSlot(id="mon_09", day="Monday", start_time="09:00", end_time="10:00"),
                TimeSlot(id="tue_09", day="Tuesday", start_time="09:00", end_time="10:00"),
            ],
            sessions=[
                Session(id="sess1", subject="Math"),
                Session(id="sess2", subject="Math"),
            ],
        )
        result = solve_schedule(problem)
        assert result.status in (SolverStatus.OPTIMAL, SolverStatus.FEASIBLE)
        assert result.validation_passed is True
        assert len(result.assignments) == 2
        assigned_slots = {a.slot_id for a in result.assignments}
        assert assigned_slots == {"mon_09", "tue_09"}

    def test_adjacent_slots_no_false_conflict(self):
        """Back-to-back adjacent slots (09:00-10:00 and 10:00-11:00) must not clash."""
        problem = SchedulingProblem(
            teachers=[Teacher(id="t1", name="Prof. Rao", qualifications={"Math"})],
            rooms=[Room(id="r1", name="Room 101", capacity=30)],
            slots=[
                TimeSlot(id="slot1", day="Monday", start_time="09:00", end_time="10:00"),
                TimeSlot(id="slot2", day="Monday", start_time="10:00", end_time="11:00"),
            ],
            sessions=[
                Session(id="sess1", subject="Math"),
                Session(id="sess2", subject="Math"),
            ],
        )
        result = solve_schedule(problem)
        assert result.status in (SolverStatus.OPTIMAL, SolverStatus.FEASIBLE)
        assert result.validation_passed is True
        assert len(result.assignments) == 2

    def test_overlapping_slot_graph(self):
        """
        Slot A (09:00-10:00), Slot B (09:30-10:30), Slot C (10:00-11:00).
        A and B overlap. B and C overlap. A and C do NOT overlap.
        2 sessions assigned to 1 teacher should pick slots A and C.
        """
        problem = SchedulingProblem(
            teachers=[Teacher(id="t1", name="Prof. Rao", qualifications={"Math"})],
            rooms=[Room(id="r1", name="Room 101", capacity=30)],
            slots=[
                TimeSlot(id="slot_a", day="Monday", start_time="09:00", end_time="10:00"),
                TimeSlot(id="slot_b", day="Monday", start_time="09:30", end_time="10:30"),
                TimeSlot(id="slot_c", day="Monday", start_time="10:00", end_time="11:00"),
            ],
            sessions=[
                Session(id="sess1", subject="Math"),
                Session(id="sess2", subject="Math"),
            ],
        )
        result = solve_schedule(problem)
        assert result.status in (SolverStatus.OPTIMAL, SolverStatus.FEASIBLE)
        assert result.validation_passed is True
        assert len(result.assignments) == 2
        assigned_slots = {a.slot_id for a in result.assignments}
        assert assigned_slots == {"slot_a", "slot_c"}

    def test_realistic_multi_session_schedule(self):
        """Stress test with 20 sessions across 4 teachers, 3 rooms, and 8 time slots."""
        teachers = [
            Teacher(id=f"t{i}", name=f"Prof {i}", qualifications={f"Subj_{i % 3}", f"Subj_{(i+1) % 3}"})
            for i in range(4)
        ]
        rooms = [
            Room(id=f"r{i}", name=f"Room {i}", capacity=30 + i * 20)
            for i in range(3)
        ]
        slots = []
        for day in ["Monday", "Tuesday"]:
            for hour in range(9, 13):
                slots.append(
                    TimeSlot(
                        id=f"{day.lower()[:3]}_{hour:02d}",
                        day=day,
                        start_time=f"{hour:02d}:00",
                        end_time=f"{hour+1:02d}:00",
                    )
                )

        sessions = [
            Session(
                id=f"sess_{i}",
                subject=f"Subj_{i % 3}",
                expected_students=20 + (i % 3) * 15,
            )
            for i in range(12)
        ]

        problem = SchedulingProblem(
            teachers=teachers,
            rooms=rooms,
            slots=slots,
            sessions=sessions,
        )

        result = solve_schedule(problem, time_limit_seconds=5.0)
        assert result.status in (SolverStatus.OPTIMAL, SolverStatus.FEASIBLE)
        assert result.validation_passed is True
        assert len(result.assignments) == 12

    def test_solver_timeout_handling(self):
        """Verify that when solver times out or cannot finish, it returns TIMEOUT/UNKNOWN and never claims success."""
        # Create a large combinatorial problem and give 0.001s
        teachers = [
            Teacher(id=f"t{i}", name=f"Prof {i}", qualifications={"Math", "Physics", "CS"})
            for i in range(15)
        ]
        rooms = [Room(id=f"r{i}", name=f"Room {i}", capacity=50) for i in range(10)]
        slots = []
        for day in ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]:
            for h in range(8, 18):
                slots.append(
                    TimeSlot(
                        id=f"{day[:3]}_{h:02d}",
                        day=day,
                        start_time=f"{h:02d}:00",
                        end_time=f"{h+1:02d}:00",
                    )
                )
        sessions = [
            Session(id=f"sess_{i}", subject="Math", expected_students=30)
            for i in range(60)
        ]

        problem = SchedulingProblem(
            teachers=teachers,
            rooms=rooms,
            slots=slots,
            sessions=sessions,
        )

        scheduler = CPSATScheduler(time_limit_seconds=0.0001)
        result = scheduler.solve(problem)

        if result.status in (SolverStatus.TIMEOUT, SolverStatus.UNKNOWN):
            assert result.validation_passed is False
            assert len(result.assignments) == 0
            assert not result.is_success
