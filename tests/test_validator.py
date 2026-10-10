"""Unit tests for the independent schedule validator."""

import pytest
from gecompose.models import (
    Room,
    ScheduledAssignment,
    SchedulingProblem,
    Session,
    Teacher,
    TimeSlot,
)
from gecompose.validator import verify_schedule


@pytest.fixture
def valid_problem_and_assignments():
    problem = SchedulingProblem(
        teachers=[
            Teacher(id="t1", name="Prof. Rao", qualifications={"Math"}, unavailable_slots={"s2"}),
            Teacher(id="t2", name="Prof. Mehta", qualifications={"Physics"}),
        ],
        rooms=[
            Room(id="r1", name="Room 101", capacity=50),
            Room(id="r2", name="Room 102", capacity=30, unavailable_slots={"s1"}),
        ],
        slots=[
            TimeSlot(id="s1", day="Monday", start_time="09:00", end_time="10:00"),
            TimeSlot(id="s2", day="Monday", start_time="10:00", end_time="11:00"),
        ],
        sessions=[
            Session(id="sess1", subject="Math", expected_students=40),
            Session(id="sess2", subject="Physics", expected_students=25),
        ],
    )

    assignments = [
        ScheduledAssignment(session_id="sess1", teacher_id="t1", room_id="r1", slot_id="s1"),
        ScheduledAssignment(session_id="sess2", teacher_id="t2", room_id="r2", slot_id="s2"),
    ]

    return problem, assignments


def test_validator_passes_on_valid_schedule(valid_problem_and_assignments):
    problem, assignments = valid_problem_and_assignments
    is_valid, violations = verify_schedule(problem, assignments)
    assert is_valid is True
    assert len(violations) == 0


def test_validator_fails_missing_session(valid_problem_and_assignments):
    problem, assignments = valid_problem_and_assignments
    incomplete_assignments = [assignments[0]]  # sess2 missing
    is_valid, violations = verify_schedule(problem, incomplete_assignments)
    assert is_valid is False
    assert any("Required sessions not scheduled" in v for v in violations)


def test_validator_fails_duplicate_session(valid_problem_and_assignments):
    problem, assignments = valid_problem_and_assignments
    duplicate_assignments = [
        assignments[0],
        ScheduledAssignment(session_id="sess1", teacher_id="t1", room_id="r1", slot_id="s2"),
    ]
    is_valid, violations = verify_schedule(problem, duplicate_assignments)
    assert is_valid is False
    assert any("multiple times" in v for v in violations)


def test_validator_fails_teacher_unavailable(valid_problem_and_assignments):
    problem, assignments = valid_problem_and_assignments
    # t1 is unavailable at s2
    bad_assignments = [
        ScheduledAssignment(session_id="sess1", teacher_id="t1", room_id="r1", slot_id="s2"),
        ScheduledAssignment(session_id="sess2", teacher_id="t2", room_id="r2", slot_id="s1"),
    ]
    is_valid, violations = verify_schedule(problem, bad_assignments)
    assert is_valid is False
    assert any("is unavailable at slot" in v for v in violations)


def test_validator_fails_room_unavailable(valid_problem_and_assignments):
    problem, assignments = valid_problem_and_assignments
    # r2 is unavailable at s1
    bad_assignments = [
        ScheduledAssignment(session_id="sess1", teacher_id="t1", room_id="r1", slot_id="s1"),
        ScheduledAssignment(session_id="sess2", teacher_id="t2", room_id="r2", slot_id="s1"),
    ]
    is_valid, violations = verify_schedule(problem, bad_assignments)
    assert is_valid is False
    assert any("Room 'r2'" in v and "unavailable" in v for v in violations)


def test_validator_fails_unqualified_teacher(valid_problem_and_assignments):
    problem, assignments = valid_problem_and_assignments
    # t2 (Physics) assigned to sess1 (Math)
    bad_assignments = [
        ScheduledAssignment(session_id="sess1", teacher_id="t2", room_id="r1", slot_id="s1"),
        ScheduledAssignment(session_id="sess2", teacher_id="t1", room_id="r2", slot_id="s2"),
    ]
    is_valid, violations = verify_schedule(problem, bad_assignments)
    assert is_valid is False
    assert any("lacks required qualification" in v for v in violations)


def test_validator_fails_room_capacity_exceeded(valid_problem_and_assignments):
    problem, assignments = valid_problem_and_assignments
    # sess1 (40 students) in r2 (capacity 30)
    bad_assignments = [
        ScheduledAssignment(session_id="sess1", teacher_id="t1", room_id="r2", slot_id="s2"),
        ScheduledAssignment(session_id="sess2", teacher_id="t2", room_id="r1", slot_id="s1"),
    ]
    is_valid, violations = verify_schedule(problem, bad_assignments)
    assert is_valid is False
    assert any("less than expected students" in v for v in violations)


def test_validator_fails_teacher_double_booking():
    problem = SchedulingProblem(
        teachers=[Teacher(id="t1", name="Prof. Rao", qualifications={"Math"})],
        rooms=[
            Room(id="r1", name="Room 101", capacity=50),
            Room(id="r2", name="Room 102", capacity=50),
        ],
        slots=[
            TimeSlot(id="s1", day="Monday", start_time="09:00", end_time="10:00"),
            TimeSlot(id="s2_overlap", day="Monday", start_time="09:30", end_time="10:30"),
        ],
        sessions=[
            Session(id="c1", subject="Math"),
            Session(id="c2", subject="Math"),
        ],
    )

    # t1 assigned to both sessions in overlapping slots s1 and s2_overlap
    assignments = [
        ScheduledAssignment(session_id="c1", teacher_id="t1", room_id="r1", slot_id="s1"),
        ScheduledAssignment(session_id="c2", teacher_id="t1", room_id="r2", slot_id="s2_overlap"),
    ]

    is_valid, violations = verify_schedule(problem, assignments)
    assert is_valid is False
    assert any("Teacher 't1' is double-booked" in v for v in violations)


def test_validator_fails_room_double_booking():
    problem = SchedulingProblem(
        teachers=[
            Teacher(id="t1", name="Prof. Rao", qualifications={"Math"}),
            Teacher(id="t2", name="Prof. Mehta", qualifications={"Math"}),
        ],
        rooms=[Room(id="r1", name="Room 101", capacity=50)],
        slots=[
            TimeSlot(id="s1", day="Monday", start_time="09:00", end_time="10:00"),
            TimeSlot(id="s2_overlap", day="Monday", start_time="09:30", end_time="10:30"),
        ],
        sessions=[
            Session(id="c1", subject="Math"),
            Session(id="c2", subject="Math"),
        ],
    )

    # r1 assigned to both sessions in overlapping slots
    assignments = [
        ScheduledAssignment(session_id="c1", teacher_id="t1", room_id="r1", slot_id="s1"),
        ScheduledAssignment(session_id="c2", teacher_id="t2", room_id="r1", slot_id="s2_overlap"),
    ]

    is_valid, violations = verify_schedule(problem, assignments)
    assert is_valid is False
    assert any("Room 'r1' is double-booked" in v for v in violations)
