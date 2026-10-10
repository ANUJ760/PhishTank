"""Domain models and schemas for the GeCompose scheduling engine."""

from __future__ import annotations

from enum import Enum
import re
from typing import Any
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


def parse_time_to_minutes(time_str: str) -> int:
    """Parse 'HH:MM' or 'HH:MM:SS' time string into minutes from midnight.
    
    Raises:
        ValueError: If time_str is invalid.
    """
    cleaned = time_str.strip()
    match = re.fullmatch(r"^(\d{1,2}):(\d{2})(?::(\d{2}))?$", cleaned)
    if not match:
        raise ValueError(f"Invalid time format '{time_str}'. Expected 'HH:MM' or 'HH:MM:SS'.")
    
    hours, minutes, _ = match.groups()
    h = int(hours)
    m = int(minutes)
    if not (0 <= h <= 23):
        raise ValueError(f"Hour out of range (0-23): {h} in '{time_str}'")
    if not (0 <= m <= 59):
        raise ValueError(f"Minute out of range (0-59): {m} in '{time_str}'")
    
    return h * 60 + m


class TimeSlot(BaseModel):
    """Represents a scheduled period on a specific day."""
    model_config = ConfigDict(frozen=True)

    id: str = Field(..., min_length=1, description="Unique identifier for the time slot")
    day: str = Field(..., min_length=1, description="Day of the week or date string")
    start_time: str = Field(..., description="Start time (e.g., '09:00')")
    end_time: str = Field(..., description="End time (e.g., '10:00')")

    @field_validator("id", "day", mode="before")
    @classmethod
    def strip_strings(cls, v: Any) -> Any:
        if isinstance(v, str):
            v = v.strip()
            if not v:
                raise ValueError("Value cannot be empty or whitespace.")
        return v

    @property
    def start_minute(self) -> int:
        return parse_time_to_minutes(self.start_time)

    @property
    def end_minute(self) -> int:
        return parse_time_to_minutes(self.end_time)

    @property
    def duration_minutes(self) -> int:
        return self.end_minute - self.start_minute

    @model_validator(mode="after")
    def validate_time_range(self) -> TimeSlot:
        start_m = parse_time_to_minutes(self.start_time)
        end_m = parse_time_to_minutes(self.end_time)
        if end_m <= start_m:
            raise ValueError(
                f"TimeSlot '{self.id}': end_time '{self.end_time}' ({end_m}m) "
                f"must be strictly after start_time '{self.start_time}' ({start_m}m)."
            )
        return self

    def overlaps(self, other: TimeSlot) -> bool:
        """Check if two time slots overlap in time.
        
        Two slots overlap if they occur on the same day and their time intervals intersect.
        """
        if self.id == other.id:
            return True
        if self.day.lower() != other.day.lower():
            return False
        return max(self.start_minute, other.start_minute) < min(self.end_minute, other.end_minute)


class Teacher(BaseModel):
    """Represents an instructor who can teach sessions."""
    model_config = ConfigDict(frozen=True)

    id: str = Field(..., min_length=1, description="Unique instructor identifier")
    name: str = Field(..., min_length=1, description="Instructor name")
    qualifications: set[str] = Field(default_factory=set, description="Set of subject qualifications")
    unavailable_slots: set[str] = Field(default_factory=set, description="Set of unavailable TimeSlot IDs")

    @field_validator("id", "name", mode="before")
    @classmethod
    def strip_strings(cls, v: Any) -> Any:
        if isinstance(v, str):
            v = v.strip()
            if not v:
                raise ValueError("Value cannot be empty or whitespace.")
        return v


class Room(BaseModel):
    """Represents a physical room or laboratory."""
    model_config = ConfigDict(frozen=True)

    id: str = Field(..., min_length=1, description="Unique room identifier")
    name: str = Field(..., min_length=1, description="Room name / code")
    capacity: int = Field(default=0, ge=0, description="Maximum student seating capacity")
    unavailable_slots: set[str] = Field(default_factory=set, description="Set of unavailable TimeSlot IDs")

    @field_validator("id", "name", mode="before")
    @classmethod
    def strip_strings(cls, v: Any) -> Any:
        if isinstance(v, str):
            v = v.strip()
            if not v:
                raise ValueError("Value cannot be empty or whitespace.")
        return v


class Session(BaseModel):
    """Represents a lecture, lab, or class session that must be scheduled."""
    model_config = ConfigDict(frozen=True)

    id: str = Field(..., min_length=1, description="Unique session identifier")
    title: str = Field(default="", description="Session title or course name")
    subject: str | None = Field(default=None, description="Course subject name")
    required_qualification: str | None = Field(
        default=None, 
        description="Explicit required teacher qualification (falls back to subject if None)"
    )
    expected_students: int = Field(default=0, ge=0, description="Expected student enrollment count")
    
    # Specific hard pinning constraints
    pinned_teacher_id: str | None = Field(default=None, description="Explicitly assigned teacher ID")
    pinned_room_id: str | None = Field(default=None, description="Explicitly assigned room ID")
    pinned_slot_id: str | None = Field(default=None, description="Explicitly assigned time slot ID")

    # Allowed subsets (if restricted)
    allowed_teacher_ids: set[str] | None = Field(default=None, description="Allowed teacher IDs")
    allowed_room_ids: set[str] | None = Field(default=None, description="Allowed room IDs")
    allowed_slot_ids: set[str] | None = Field(default=None, description="Allowed slot IDs")

    @field_validator("id", mode="before")
    @classmethod
    def strip_id(cls, v: Any) -> Any:
        if isinstance(v, str):
            v = v.strip()
            if not v:
                raise ValueError("Session ID cannot be empty or whitespace.")
        return v

    @property
    def effective_qualification(self) -> str | None:
        """Returns the qualification needed to teach this session, if any."""
        return self.required_qualification or self.subject


class SchedulingProblem(BaseModel):
    """Validated input container for the scheduling solver."""
    model_config = ConfigDict(frozen=True)

    teachers: list[Teacher] = Field(default_factory=list)
    rooms: list[Room] = Field(default_factory=list)
    slots: list[TimeSlot] = Field(default_factory=list)
    sessions: list[Session] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_entities_and_references(self) -> SchedulingProblem:
        # Check uniqueness of IDs
        teacher_ids = [t.id for t in self.teachers]
        if len(teacher_ids) != len(set(teacher_ids)):
            duplicates = [t_id for t_id in teacher_ids if teacher_ids.count(t_id) > 1]
            raise ValueError(f"Duplicate teacher IDs found: {set(duplicates)}")

        room_ids = [r.id for r in self.rooms]
        if len(room_ids) != len(set(room_ids)):
            duplicates = [r_id for r_id in room_ids if room_ids.count(r_id) > 1]
            raise ValueError(f"Duplicate room IDs found: {set(duplicates)}")

        slot_ids = [s.id for s in self.slots]
        if len(slot_ids) != len(set(slot_ids)):
            duplicates = [s_id for s_id in slot_ids if slot_ids.count(s_id) > 1]
            raise ValueError(f"Duplicate slot IDs found: {set(duplicates)}")

        session_ids = [sess.id for sess in self.sessions]
        if len(session_ids) != len(set(session_ids)):
            duplicates = [sess_id for sess_id in session_ids if session_ids.count(sess_id) > 1]
            raise ValueError(f"Duplicate session IDs found: {set(duplicates)}")

        valid_teacher_set = set(teacher_ids)
        valid_room_set = set(room_ids)
        valid_slot_set = set(slot_ids)

        # Validate teacher unavailable_slots reference existing slots
        for teacher in self.teachers:
            invalid_slots = teacher.unavailable_slots - valid_slot_set
            if invalid_slots:
                raise ValueError(
                    f"Teacher '{teacher.id}' references non-existent unavailable slots: {invalid_slots}"
                )

        # Validate room unavailable_slots reference existing slots
        for room in self.rooms:
            invalid_slots = room.unavailable_slots - valid_slot_set
            if invalid_slots:
                raise ValueError(
                    f"Room '{room.id}' references non-existent unavailable slots: {invalid_slots}"
                )

        # Validate session references
        for sess in self.sessions:
            if sess.pinned_teacher_id and sess.pinned_teacher_id not in valid_teacher_set:
                raise ValueError(
                    f"Session '{sess.id}' references non-existent pinned teacher '{sess.pinned_teacher_id}'"
                )
            if sess.pinned_room_id and sess.pinned_room_id not in valid_room_set:
                raise ValueError(
                    f"Session '{sess.id}' references non-existent pinned room '{sess.pinned_room_id}'"
                )
            if sess.pinned_slot_id and sess.pinned_slot_id not in valid_slot_set:
                raise ValueError(
                    f"Session '{sess.id}' references non-existent pinned slot '{sess.pinned_slot_id}'"
                )

            if sess.allowed_teacher_ids is not None:
                invalid_t = sess.allowed_teacher_ids - valid_teacher_set
                if invalid_t:
                    raise ValueError(
                        f"Session '{sess.id}' references non-existent allowed teachers: {invalid_t}"
                    )
                if sess.pinned_teacher_id and sess.pinned_teacher_id not in sess.allowed_teacher_ids:
                    raise ValueError(
                        f"Session '{sess.id}' pinned teacher '{sess.pinned_teacher_id}' "
                        f"is not in its allowed_teacher_ids: {sess.allowed_teacher_ids}"
                    )

            if sess.allowed_room_ids is not None:
                invalid_r = sess.allowed_room_ids - valid_room_set
                if invalid_r:
                    raise ValueError(
                        f"Session '{sess.id}' references non-existent allowed rooms: {invalid_r}"
                    )
                if sess.pinned_room_id and sess.pinned_room_id not in sess.allowed_room_ids:
                    raise ValueError(
                        f"Session '{sess.id}' pinned room '{sess.pinned_room_id}' "
                        f"is not in its allowed_room_ids: {sess.allowed_room_ids}"
                    )

            if sess.allowed_slot_ids is not None:
                invalid_s = sess.allowed_slot_ids - valid_slot_set
                if invalid_s:
                    raise ValueError(
                        f"Session '{sess.id}' references non-existent allowed slots: {invalid_s}"
                    )
                if sess.pinned_slot_id and sess.pinned_slot_id not in sess.allowed_slot_ids:
                    raise ValueError(
                        f"Session '{sess.id}' pinned slot '{sess.pinned_slot_id}' "
                        f"is not in its allowed_slot_ids: {sess.allowed_slot_ids}"
                    )

        return self


class SolverStatus(str, Enum):
    """Outcome status returned by the CP-SAT solver."""
    OPTIMAL = "OPTIMAL"
    FEASIBLE = "FEASIBLE"
    INFEASIBLE = "INFEASIBLE"
    TIMEOUT = "TIMEOUT"
    UNKNOWN = "UNKNOWN"
    INVALID_INPUT = "INVALID_INPUT"


class ScheduledAssignment(BaseModel):
    """An individual session placement in the schedule."""
    model_config = ConfigDict(frozen=True)

    session_id: str = Field(..., description="Scheduled session identifier")
    teacher_id: str = Field(..., description="Assigned teacher identifier")
    room_id: str = Field(..., description="Assigned room identifier")
    slot_id: str = Field(..., description="Assigned time slot identifier")


class ScheduleResult(BaseModel):
    """Complete result returned from the scheduling solver."""
    model_config = ConfigDict(frozen=True)

    status: SolverStatus = Field(..., description="Status of the solving process")
    assignments: list[ScheduledAssignment] = Field(
        default_factory=list, 
        description="List of verified session assignments"
    )
    wall_time_seconds: float = Field(default=0.0, ge=0.0, description="Solve time in seconds")
    message: str | None = Field(default=None, description="Informative status message")
    validation_passed: bool = Field(
        default=False, 
        description="Whether an independent constraint check fully passed"
    )
    violations: list[str] = Field(
        default_factory=list, 
        description="List of constraint violations found during verification"
    )
    statistics: dict[str, Any] = Field(
        default_factory=dict, 
        description="Additional solver statistics and metrics"
    )

    @property
    def is_success(self) -> bool:
        """Returns True only if the solver found a solution AND independent verification passed."""
        return self.status in (SolverStatus.OPTIMAL, SolverStatus.FEASIBLE) and self.validation_passed
