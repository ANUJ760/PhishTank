"""Unit and integration tests for conflict diagnosis and MUS extraction."""

import pytest
from gecompose.diagnostics import ConflictDiagnoser, diagnose_conflicts
from gecompose.models import (
    ConstraintType,
    Room,
    SchedulingProblem,
    Session,
    SolverStatus,
    Teacher,
    TimeSlot,
)


class TestConflictDiagnosis:
    def test_feasible_problem_produces_no_conflict(self):
        """Feasible input must return is_infeasible=False and no conflict constraints."""
        problem = SchedulingProblem(
            teachers=[Teacher(id="t1", name="Prof. Rao", qualifications={"Math"})],
            rooms=[Room(id="r1", name="Room 101", capacity=40)],
            slots=[TimeSlot(id="s1", day="Monday", start_time="09:00", end_time="10:00")],
            sessions=[Session(id="c1", subject="Math", expected_students=30)],
        )
        diag = diagnose_conflicts(problem)
        assert diag.is_infeasible is False
        assert diag.has_core is False
        assert diag.status == SolverStatus.FEASIBLE

    def test_teacher_unavailability_conflict_diagnosed(self):
        """Diagnose conflict when pinned session clashes with teacher unavailability."""
        problem = SchedulingProblem(
            teachers=[
                Teacher(
                    id="t_rao",
                    name="Prof. Rao",
                    qualifications={"Databases"},
                    unavailable_slots={"mon_09"},
                )
            ],
            rooms=[Room(id="r1", name="Lab 1", capacity=50)],
            slots=[
                TimeSlot(id="mon_09", day="Monday", start_time="09:00", end_time="10:00"),
                TimeSlot(id="mon_10", day="Monday", start_time="10:00", end_time="11:00"),
            ],
            sessions=[
                Session(
                    id="sess_db",
                    subject="Databases",
                    pinned_teacher_id="t_rao",
                    pinned_slot_id="mon_09",
                )
            ],
        )

        diag = diagnose_conflicts(problem)
        assert diag.is_infeasible is True
        assert diag.is_minimal is True
        assert diag.has_core is True

        c_types = {c.constraint_type for c in diag.conflicting_constraints}
        assert ConstraintType.SESSION_REQUIRED in c_types
        assert ConstraintType.PINNED_SLOT in c_types
        assert ConstraintType.TEACHER_UNAVAILABLE in c_types

        # Check diagnosed entities
        assert "sess_db" in diag.diagnosed_entities["sessions"]
        assert "t_rao" in diag.diagnosed_entities["teachers"]
        assert "mon_09" in diag.diagnosed_entities["slots"]

    def test_teacher_overlap_conflict_diagnosed(self):
        """Diagnose conflict when two sessions are pinned to the same teacher at the same slot."""
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

        diag = diagnose_conflicts(problem)
        assert diag.is_infeasible is True
        assert diag.is_minimal is True
        c_types = {c.constraint_type for c in diag.conflicting_constraints}
        assert ConstraintType.TEACHER_NON_OVERLAP in c_types
        assert "c1" in diag.diagnosed_entities["sessions"]
        assert "c2" in diag.diagnosed_entities["sessions"]

    def test_room_overlap_conflict_diagnosed(self):
        """Diagnose conflict when two sessions are pinned to the same room at the same slot."""
        problem = SchedulingProblem(
            teachers=[
                Teacher(id="t1", name="Prof. A", qualifications={"Math"}),
                Teacher(id="t2", name="Prof. B", qualifications={"Math"}),
            ],
            rooms=[Room(id="r1", name="Room 1", capacity=50)],
            slots=[TimeSlot(id="s1", day="Monday", start_time="09:00", end_time="10:00")],
            sessions=[
                Session(id="c1", subject="Math", pinned_room_id="r1", pinned_slot_id="s1"),
                Session(id="c2", subject="Math", pinned_room_id="r1", pinned_slot_id="s1"),
            ],
        )

        diag = diagnose_conflicts(problem)
        assert diag.is_infeasible is True
        assert diag.is_minimal is True
        c_types = {c.constraint_type for c in diag.conflicting_constraints}
        assert ConstraintType.ROOM_NON_OVERLAP in c_types
        assert "r1" in diag.diagnosed_entities["rooms"]

    def test_qualification_shortage_diagnosed(self):
        """Diagnose conflict when no teacher has the required qualification."""
        problem = SchedulingProblem(
            teachers=[Teacher(id="t1", name="Prof. Rao", qualifications={"Math"})],
            rooms=[Room(id="r1", name="Room 1", capacity=50)],
            slots=[TimeSlot(id="s1", day="Monday", start_time="09:00", end_time="10:00")],
            sessions=[Session(id="c1", subject="Quantum Computing")],
        )

        diag = diagnose_conflicts(problem)
        assert diag.is_infeasible is True
        assert diag.is_minimal is True
        c_types = {c.constraint_type for c in diag.conflicting_constraints}
        assert ConstraintType.TEACHER_QUALIFICATION in c_types
        assert "c1" in diag.diagnosed_entities["sessions"]

    def test_room_capacity_shortage_diagnosed(self):
        """Diagnose conflict when room capacity is less than required students."""
        problem = SchedulingProblem(
            teachers=[Teacher(id="t1", name="Prof. Rao", qualifications={"Math"})],
            rooms=[Room(id="r1", name="Room 1", capacity=30)],
            slots=[TimeSlot(id="s1", day="Monday", start_time="09:00", end_time="10:00")],
            sessions=[Session(id="c1", subject="Math", expected_students=100)],
        )

        diag = diagnose_conflicts(problem)
        assert diag.is_infeasible is True
        assert diag.is_minimal is True
        c_types = {c.constraint_type for c in diag.conflicting_constraints}
        assert ConstraintType.ROOM_CAPACITY in c_types

    def test_non_minimal_labeling_accuracy(self):
        """When minimizer is disabled, is_minimal is only True if core size <= 1, else correctly labeled."""
        problem = SchedulingProblem(
            teachers=[
                Teacher(
                    id="t1",
                    name="Prof. Rao",
                    qualifications={"Math"},
                    unavailable_slots={"s1"},
                )
            ],
            rooms=[Room(id="r1", name="Room 1", capacity=50)],
            slots=[TimeSlot(id="s1", day="Monday", start_time="09:00", end_time="10:00")],
            sessions=[
                Session(id="c1", subject="Math", pinned_teacher_id="t1", pinned_slot_id="s1")
            ],
        )

        diagnoser = ConflictDiagnoser(timeout_seconds=5.0, minimize_core=False)
        diag = diagnoser.diagnose(problem)
        assert diag.is_infeasible is True
        # Either the raw core was size 1 or it is labeled with its verified status
        if len(diag.conflicting_constraints) > 1:
            assert diag.is_minimal is False

    def test_allowed_slots_conflict_diagnosed(self):
        """Diagnose conflict when allowed slots are completely unavailable to the teacher."""
        problem = SchedulingProblem(
            teachers=[
                Teacher(
                    id="t1",
                    name="Prof. Rao",
                    qualifications={"Math"},
                    unavailable_slots={"s1"},
                )
            ],
            rooms=[Room(id="r1", name="Room 1", capacity=50)],
            slots=[
                TimeSlot(id="s1", day="Monday", start_time="09:00", end_time="10:00"),
                TimeSlot(id="s2", day="Monday", start_time="10:00", end_time="11:00"),
            ],
            sessions=[
                Session(
                    id="c1",
                    subject="Math",
                    pinned_teacher_id="t1",
                    allowed_slot_ids={"s1"},  # Only allowed at s1, but t1 is unavailable at s1
                )
            ],
        )

        diag = diagnose_conflicts(problem)
        assert diag.is_infeasible is True
        assert diag.is_minimal is True
        c_types = {c.constraint_type for c in diag.conflicting_constraints}
        assert ConstraintType.ALLOWED_SLOTS in c_types
        assert ConstraintType.TEACHER_UNAVAILABLE in c_types

    def test_timeout_diagnosis_does_not_fabricate_conflict(self):
        """Verify that when diagnosis times out, it does not invent/fabricate a conflict core."""
        teachers = [
            Teacher(id=f"t{i}", name=f"Prof {i}", qualifications={"Math"})
            for i in range(3)
        ]
        rooms = [Room(id=f"r{i}", name=f"Room {i}", capacity=50) for i in range(2)]
        slots = [
            TimeSlot(
                id=f"s_{i}",
                day=f"Day_{i%2}",
                start_time=f"{(i%3)+9:02d}:00",
                end_time=f"{(i%3)+10:02d}:00",
            )
            for i in range(4)
        ]
        sessions = [
            Session(id=f"sess_{i}", subject="Math", expected_students=30)
            for i in range(6)
        ]

        problem = SchedulingProblem(
            teachers=teachers,
            rooms=rooms,
            slots=slots,
            sessions=sessions,
        )

        diagnoser = ConflictDiagnoser(timeout_seconds=0.0001)
        diag = diagnoser.diagnose(problem)

        if diag.status in (SolverStatus.TIMEOUT, SolverStatus.UNKNOWN):
            assert diag.is_infeasible is False
            assert diag.is_minimal is False
            assert len(diag.conflicting_constraints) == 0
            assert "timed out" in diag.explanation.lower() or "unknown" in diag.explanation.lower()

