"""Unit tests for GeCompose data models and validation."""

import pytest
from pydantic import ValidationError

from gecompose.models import (
    Room,
    ScheduledAssignment,
    ScheduleResult,
    SchedulingProblem,
    Session,
    SolverStatus,
    Teacher,
    TimeSlot,
    parse_time_to_minutes,
)


class TestTimeSlot:
    def test_valid_timeslot_creation(self):
        slot = TimeSlot(id="slot1", day="Monday", start_time="09:00", end_time="10:00")
        assert slot.id == "slot1"
        assert slot.day == "Monday"
        assert slot.start_minute == 540
        assert slot.end_minute == 600
        assert slot.duration_minutes == 60

    def test_parse_time_to_minutes(self):
        assert parse_time_to_minutes("00:00") == 0
        assert parse_time_to_minutes("09:30") == 570
        assert parse_time_to_minutes("23:59") == 1439
        assert parse_time_to_minutes("14:30:00") == 870

        with pytest.raises(ValueError):
            parse_time_to_minutes("invalid")
        with pytest.raises(ValueError):
            parse_time_to_minutes("25:00")
        with pytest.raises(ValueError):
            parse_time_to_minutes("10:65")

    def test_timeslot_invalid_range(self):
        # End time before start time
        with pytest.raises(ValidationError):
            TimeSlot(id="s1", day="Mon", start_time="10:00", end_time="09:00")
        # End time equal to start time
        with pytest.raises(ValidationError):
            TimeSlot(id="s2", day="Mon", start_time="10:00", end_time="10:00")

    def test_timeslot_overlap_logic(self):
        slot_mon_9_10 = TimeSlot(id="s1", day="Monday", start_time="09:00", end_time="10:00")
        slot_mon_930_1030 = TimeSlot(id="s2", day="Monday", start_time="09:30", end_time="10:30")
        slot_mon_10_11 = TimeSlot(id="s3", day="Monday", start_time="10:00", end_time="11:00")
        slot_tue_9_10 = TimeSlot(id="s4", day="Tuesday", start_time="09:00", end_time="10:00")

        # Identity
        assert slot_mon_9_10.overlaps(slot_mon_9_10)

        # Overlapping on same day
        assert slot_mon_9_10.overlaps(slot_mon_930_1030)
        assert slot_mon_930_1030.overlaps(slot_mon_9_10)

        # Adjacent on same day (touching boundaries does not count as overlap)
        assert not slot_mon_9_10.overlaps(slot_mon_10_11)
        assert not slot_mon_10_11.overlaps(slot_mon_9_10)

        # Different day with identical time
        assert not slot_mon_9_10.overlaps(slot_tue_9_10)


class TestEntityValidation:
    def test_teacher_validation(self):
        teacher = Teacher(id="t1", name="Prof. Rao", qualifications={"Math", "Physics"})
        assert teacher.id == "t1"
        assert "Math" in teacher.qualifications

        with pytest.raises(ValidationError):
            Teacher(id="", name="Empty ID")
        with pytest.raises(ValidationError):
            Teacher(id="t2", name="")

    def test_room_validation(self):
        room = Room(id="r101", name="Lab A", capacity=30)
        assert room.capacity == 30

        with pytest.raises(ValidationError):
            Room(id="r102", name="Lab B", capacity=-5)

    def test_session_validation(self):
        session = Session(
            id="sess1",
            title="Database Systems",
            subject="Databases",
            expected_students=45,
            pinned_teacher_id="t1",
        )
        assert session.effective_qualification == "Databases"

        # Explicit qualification override
        session2 = Session(
            id="sess2",
            subject="Databases",
            required_qualification="AdvDB",
            expected_students=20,
        )
        assert session2.effective_qualification == "AdvDB"


class TestSchedulingProblemValidation:
    @pytest.fixture
    def basic_problem_data(self):
        return {
            "teachers": [
                Teacher(id="t1", name="Prof. Rao", qualifications={"Math"}),
                Teacher(id="t2", name="Prof. Mehta", qualifications={"Physics"}),
            ],
            "rooms": [
                Room(id="r1", name="Room 101", capacity=40),
                Room(id="r2", name="Room 102", capacity=60),
            ],
            "slots": [
                TimeSlot(id="s1", day="Monday", start_time="09:00", end_time="10:00"),
                TimeSlot(id="s2", day="Monday", start_time="10:00", end_time="11:00"),
            ],
            "sessions": [
                Session(id="c1", subject="Math", expected_students=30),
                Session(id="c2", subject="Physics", expected_students=50),
            ],
        }

    def test_valid_problem(self, basic_problem_data):
        problem = SchedulingProblem(**basic_problem_data)
        assert len(problem.teachers) == 2
        assert len(problem.rooms) == 2
        assert len(problem.slots) == 2
        assert len(problem.sessions) == 2

    def test_duplicate_teacher_id_rejected(self, basic_problem_data):
        basic_problem_data["teachers"].append(
            Teacher(id="t1", name="Duplicate Rao", qualifications={"Math"})
        )
        with pytest.raises(ValidationError, match="Duplicate teacher IDs found"):
            SchedulingProblem(**basic_problem_data)

    def test_duplicate_room_id_rejected(self, basic_problem_data):
        basic_problem_data["rooms"].append(
            Room(id="r1", name="Duplicate Room", capacity=20)
        )
        with pytest.raises(ValidationError, match="Duplicate room IDs found"):
            SchedulingProblem(**basic_problem_data)

    def test_duplicate_slot_id_rejected(self, basic_problem_data):
        basic_problem_data["slots"].append(
            TimeSlot(id="s1", day="Tuesday", start_time="09:00", end_time="10:00")
        )
        with pytest.raises(ValidationError, match="Duplicate slot IDs found"):
            SchedulingProblem(**basic_problem_data)

    def test_duplicate_session_id_rejected(self, basic_problem_data):
        basic_problem_data["sessions"].append(
            Session(id="c1", subject="Math")
        )
        with pytest.raises(ValidationError, match="Duplicate session IDs found"):
            SchedulingProblem(**basic_problem_data)

    def test_invalid_teacher_unavailable_slot(self, basic_problem_data):
        basic_problem_data["teachers"] = [
            Teacher(id="t1", name="Prof. Rao", unavailable_slots={"non_existent_slot"})
        ]
        with pytest.raises(ValidationError, match="non-existent unavailable slots"):
            SchedulingProblem(**basic_problem_data)

    def test_invalid_room_unavailable_slot(self, basic_problem_data):
        basic_problem_data["rooms"] = [
            Room(id="r1", name="Room 101", capacity=40, unavailable_slots={"bad_slot"})
        ]
        with pytest.raises(ValidationError, match="non-existent unavailable slots"):
            SchedulingProblem(**basic_problem_data)

    def test_invalid_session_pinned_references(self, basic_problem_data):
        # Invalid pinned teacher
        basic_problem_data["sessions"] = [
            Session(id="c1", subject="Math", pinned_teacher_id="unknown_t")
        ]
        with pytest.raises(ValidationError, match="non-existent pinned teacher"):
            SchedulingProblem(**basic_problem_data)

        # Invalid pinned room
        basic_problem_data["sessions"] = [
            Session(id="c1", subject="Math", pinned_room_id="unknown_r")
        ]
        with pytest.raises(ValidationError, match="non-existent pinned room"):
            SchedulingProblem(**basic_problem_data)

        # Invalid pinned slot
        basic_problem_data["sessions"] = [
            Session(id="c1", subject="Math", pinned_slot_id="unknown_s")
        ]
        with pytest.raises(ValidationError, match="non-existent pinned slot"):
            SchedulingProblem(**basic_problem_data)

    def test_invalid_session_allowed_references(self, basic_problem_data):
        basic_problem_data["sessions"] = [
            Session(id="c1", subject="Math", allowed_teacher_ids={"unknown_t"})
        ]
        with pytest.raises(ValidationError, match="non-existent allowed teachers"):
            SchedulingProblem(**basic_problem_data)

    def test_inconsistent_pinning_and_allowed(self, basic_problem_data):
        basic_problem_data["sessions"] = [
            Session(
                id="c1",
                subject="Math",
                pinned_teacher_id="t1",
                allowed_teacher_ids={"t2"},
            )
        ]
        with pytest.raises(ValidationError, match="is not in its allowed_teacher_ids"):
            SchedulingProblem(**basic_problem_data)
