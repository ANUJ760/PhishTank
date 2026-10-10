"""Domain models and schemas for the GeCompose scheduling engine."""

from __future__ import annotations

from enum import Enum
import re
from typing import Any
from pydantic import BaseModel, ConfigDict, Field, computed_field, field_validator, model_validator


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


class ConstraintType(str, Enum):
    """Types of constraints that can participate in conflicts or relaxations."""
    SESSION_REQUIRED = "SESSION_REQUIRED"
    PINNED_TEACHER = "PINNED_TEACHER"
    PINNED_ROOM = "PINNED_ROOM"
    PINNED_SLOT = "PINNED_SLOT"
    ALLOWED_TEACHERS = "ALLOWED_TEACHERS"
    ALLOWED_ROOMS = "ALLOWED_ROOMS"
    ALLOWED_SLOTS = "ALLOWED_SLOTS"
    TEACHER_UNAVAILABLE = "TEACHER_UNAVAILABLE"
    ROOM_UNAVAILABLE = "ROOM_UNAVAILABLE"
    TEACHER_QUALIFICATION = "TEACHER_QUALIFICATION"
    ROOM_CAPACITY = "ROOM_CAPACITY"
    TEACHER_NON_OVERLAP = "TEACHER_NON_OVERLAP"
    ROOM_NON_OVERLAP = "ROOM_NON_OVERLAP"


class ConflictConstraint(BaseModel):
    """An individual constraint identified as part of an unsatisfiable conflict core."""
    model_config = ConfigDict(frozen=True)

    id: str = Field(..., description="Unique diagnostic assumption/constraint identifier")
    constraint_type: ConstraintType = Field(..., description="Semantic type of the constraint")
    description: str = Field(..., description="Human-readable factual description of the constraint")
    session_id: str | None = Field(default=None, description="Associated session ID if applicable")
    teacher_id: str | None = Field(default=None, description="Associated teacher ID if applicable")
    room_id: str | None = Field(default=None, description="Associated room ID if applicable")
    slot_id: str | None = Field(default=None, description="Associated time slot ID if applicable")
    details: dict[str, Any] = Field(default_factory=dict, description="Additional constraint metadata")


class ConflictDiagnosis(BaseModel):
    """Structured diagnosis of an infeasible or unsatisfiable scheduling problem."""
    model_config = ConfigDict(frozen=True)

    status: SolverStatus = Field(..., description="Diagnostic outcome status")
    is_infeasible: bool = Field(..., description="Whether the problem was proven infeasible")
    is_minimal: bool = Field(
        default=False, 
        description="True if the conflict core is mathematically verified to be a Minimal Unsatisfiable Subset (MUS)"
    )
    conflicting_constraints: list[ConflictConstraint] = Field(
        default_factory=list, 
        description="Structured list of constraints forming the unsatisfiable core"
    )
    explanation: str = Field(
        default="", 
        description="Factual, deterministic explanation generated directly from the conflict core"
    )
    diagnosed_entities: dict[str, list[str]] = Field(
        default_factory=dict, 
        description="IDs of participating entities (sessions, teachers, rooms, slots)"
    )
    statistics: dict[str, Any] = Field(
        default_factory=dict, 
        description="Diagnostic solver performance metrics and core reduction stats"
    )
    wall_time_seconds: float = Field(
        default=0.0, 
        ge=0.0, 
        description="Diagnosis wall time in seconds"
    )

    @property
    def has_core(self) -> bool:
        """Returns True if a non-empty conflict core was successfully identified."""
        return len(self.conflicting_constraints) > 0


class RelaxationPolicy(BaseModel):
    """Configuration governing which constraints can be softened to find alternative schedules."""
    model_config = ConfigDict(frozen=True)

    allow_slot_relaxation: bool = Field(
        default=True, 
        description="Whether pinned or restricted time slots may be relaxed"
    )
    allow_teacher_relaxation: bool = Field(
        default=True, 
        description="Whether pinned or restricted teachers may be relaxed"
    )
    allow_room_relaxation: bool = Field(
        default=True, 
        description="Whether pinned or restricted rooms may be relaxed"
    )
    relaxable_session_ids: set[str] | None = Field(
        default=None, 
        description="Subset of session IDs allowed to be relaxed. If None, all sessions are eligible."
    )
    max_alternatives: int = Field(
        default=3, 
        ge=1, 
        le=20, 
        description="Maximum number of distinct alternative schedules to return"
    )
    timeout_seconds: float = Field(
        default=5.0, 
        gt=0.0, 
        description="Time limit for alternative generation in seconds"
    )


class RelaxedRequirement(BaseModel):
    """Details of a specific constraint that was softened in an alternative schedule."""
    model_config = ConfigDict(frozen=True)

    session_id: str = Field(..., description="ID of the session whose requirement was relaxed")
    constraint_type: ConstraintType = Field(..., description="Type of constraint relaxed")
    original_value: Any = Field(..., description="Original required value (e.g. original pinned slot)")
    relaxed_value: Any = Field(..., description="Value assigned in the alternative schedule")
    description: str = Field(..., description="Human-readable description of the relaxation")


class ScheduleAlternative(BaseModel):
    """A solver-verified alternative schedule generated by relaxing select user constraints."""
    model_config = ConfigDict(frozen=True)

    alternative_id: int = Field(..., description="1-based index of this alternative")
    assignments: list[ScheduledAssignment] = Field(
        default_factory=list, 
        description="Verified session assignments"
    )
    relaxed_requirements: list[RelaxedRequirement] = Field(
        default_factory=list, 
        description="List of user requirements that were softened"
    )
    penalty_score: int = Field(
        default=0, 
        ge=0, 
        description="Total penalty metric (lower means fewer/smaller relaxations)"
    )
    validation_passed: bool = Field(
        default=False, 
        description="Whether this alternative passed independent constraint verification"
    )
    status: SolverStatus = Field(
        default=SolverStatus.FEASIBLE, 
        description="Solver status for this alternative"
    )


class AlternativeSearchResult(BaseModel):
    """Container of solver-generated, verified alternatives for an infeasible problem."""
    model_config = ConfigDict(frozen=True)

    status: SolverStatus = Field(..., description="Overall search status (FEASIBLE, INFEASIBLE, TIMEOUT, etc.)")
    original_status: SolverStatus = Field(..., description="Status of the original unrelaxed problem")
    alternatives: list[ScheduleAlternative] = Field(
        default_factory=list, 
        description="List of verified alternative schedules"
    )
    search_time_seconds: float = Field(default=0.0, ge=0.0, description="Total search time in seconds")
    message: str | None = Field(default=None, description="Informative message about the alternative search")
    statistics: dict[str, Any] = Field(default_factory=dict, description="Search statistics")


class ResourceType(str, Enum):
    """Types of resources that can experience disruptions."""
    ROOM = "room"
    TEACHER = "teacher"


class DisruptionEvent(BaseModel):
    """Represents a real-world resource unavailability or closure event."""
    model_config = ConfigDict(frozen=True)

    id: str = Field(..., min_length=1, description="Unique disruption event identifier")
    resource_type: ResourceType = Field(..., description="Type of resource disrupted ('room' or 'teacher')")
    resource_id: str = Field(..., min_length=1, description="Identifier of the unavailable room or teacher")
    slot_ids: set[str] = Field(
        default_factory=set,
        description="Explicit set of TimeSlot IDs during which the resource is unavailable"
    )
    day: str | None = Field(
        default=None,
        description="Optional day of the disruption interval (e.g., 'Monday')"
    )
    start_time: str | None = Field(
        default=None,
        description="Optional start time of the disruption interval (e.g., '09:00')"
    )
    end_time: str | None = Field(
        default=None,
        description="Optional end time of the disruption interval (e.g., '12:00')"
    )
    reason: str = Field(
        default="",
        description="Operational context or reason for the disruption"
    )

    @field_validator("id", "resource_id", mode="before")
    @classmethod
    def strip_ids(cls, v: Any) -> Any:
        if isinstance(v, str):
            v = v.strip()
            if not v:
                raise ValueError("Identifier cannot be empty or whitespace.")
        return v

    @model_validator(mode="after")
    def validate_interval_and_targets(self) -> DisruptionEvent:
        # Check time interval if provided
        if self.start_time is not None or self.end_time is not None:
            if not self.start_time or not self.end_time or not self.day:
                raise ValueError(
                    "When specifying a time interval for disruption, 'day', 'start_time', "
                    "and 'end_time' must all be provided."
                )
            start_m = parse_time_to_minutes(self.start_time)
            end_m = parse_time_to_minutes(self.end_time)
            if end_m <= start_m:
                raise ValueError(
                    f"Disruption '{self.id}': end_time '{self.end_time}' ({end_m}m) "
                    f"must be strictly after start_time '{self.start_time}' ({start_m}m)."
                )

        # Must have either slot_ids or a valid time interval
        if not self.slot_ids and not (self.day and self.start_time and self.end_time):
            raise ValueError(
                f"Disruption '{self.id}' must specify either 'slot_ids' or a valid time interval ('day', 'start_time', 'end_time')."
            )
        return self

    def resolve_unavailable_slots(self, problem: SchedulingProblem) -> set[str]:
        """Resolve all slot IDs in the given problem that are affected by this disruption."""
        slots = set(self.slot_ids)
        if self.day and self.start_time and self.end_time:
            start_m = parse_time_to_minutes(self.start_time)
            end_m = parse_time_to_minutes(self.end_time)
            for s in problem.slots:
                if s.day.lower() == self.day.lower():
                    # Overlap if max(start) < min(end)
                    if max(start_m, s.start_minute) < min(end_m, s.end_minute):
                        slots.add(s.id)
        return slots


class AssignmentChange(BaseModel):
    """Detailed record of how an individual session assignment was modified during recovery."""
    model_config = ConfigDict(frozen=True)

    session_id: str = Field(..., description="ID of the session")
    original_assignment: ScheduledAssignment = Field(..., description="Assignment prior to disruption")
    new_assignment: ScheduledAssignment = Field(..., description="Assignment in the recovered schedule")
    changed_teacher: bool = Field(default=False, description="Whether the instructor changed")
    changed_room: bool = Field(default=False, description="Whether the room changed")
    changed_slot: bool = Field(default=False, description="Whether the time slot changed")
    reason: str = Field(default="", description="Human-readable explanation of why this assignment changed")


class ImpactReport(BaseModel):
    """Impact analysis report detailing how a disruption affects an active schedule."""
    model_config = ConfigDict(frozen=True)

    disruption: DisruptionEvent = Field(..., description="The disruption event analyzed")
    directly_affected_session_ids: list[str] = Field(
        default_factory=list,
        description="IDs of sessions directly assigned to the disrupted resource during unavailable slots"
    )
    directly_affected_assignments: list[ScheduledAssignment] = Field(
        default_factory=list,
        description="Assignments invalidated by the disruption"
    )
    unaffected_session_ids: list[str] = Field(
        default_factory=list,
        description="IDs of scheduled sessions that do not conflict with the disruption"
    )
    total_scheduled_sessions: int = Field(
        default=0,
        ge=0,
        description="Total number of scheduled sessions prior to disruption"
    )

    @computed_field
    @property
    def has_impact(self) -> bool:
        """Returns True if any active assignments are directly invalidated by the disruption."""
        return len(self.directly_affected_session_ids) > 0


class RecoveryPolicy(BaseModel):
    """Configuration governing minimal-change recovery optimization."""
    model_config = ConfigDict(frozen=True)

    room_change_penalty: int = Field(default=1, ge=0, description="Penalty weight for relocating a session to another room")
    slot_change_penalty: int = Field(default=3, ge=0, description="Penalty weight for rescheduling a session to another slot")
    teacher_change_penalty: int = Field(default=10, ge=0, description="Penalty weight for swapping the assigned instructor")
    unaffected_displacement_penalty: int = Field(
        default=25,
        ge=0,
        description="Additional penalty weight for displacing an otherwise unaffected session (cascade penalty)"
    )
    allow_room_reassignment: bool = Field(default=True, description="Whether sessions may move to another eligible room")
    allow_slot_reassignment: bool = Field(default=True, description="Whether sessions may move to another eligible time slot")
    allow_teacher_reassignment: bool = Field(default=True, description="Whether sessions may be reassigned to another qualified teacher")
    time_limit_seconds: float = Field(default=10.0, gt=0.0, description="Solver time budget for recovery search in seconds")


class DisruptionRecoveryResult(BaseModel):
    """Outcome report for minimal-change schedule recovery after a disruption."""
    model_config = ConfigDict(frozen=True)

    disruption: DisruptionEvent = Field(..., description="The disruption event that triggered recovery")
    status: SolverStatus = Field(..., description="Solver status of the recovery attempt")
    original_assignments: list[ScheduledAssignment] = Field(
        default_factory=list,
        description="Schedule assignments prior to disruption"
    )
    recovered_assignments: list[ScheduledAssignment] = Field(
        default_factory=list,
        description="Verified replacement schedule assignments (if feasible/optimal)"
    )
    directly_affected_session_ids: list[str] = Field(
        default_factory=list,
        description="Sessions directly conflicting with the disruption"
    )
    moved_session_ids: list[str] = Field(
        default_factory=list,
        description="All sessions whose assignments changed in the recovery schedule"
    )
    unaffected_session_ids: list[str] = Field(
        default_factory=list,
        description="Sessions that remained in their original assignments"
    )
    changes: list[AssignmentChange] = Field(
        default_factory=list,
        description="Itemized changes between original and recovered schedule"
    )
    total_penalty: int = Field(default=0, ge=0, description="Total weighted change penalty score")
    validation_passed: bool = Field(
        default=False,
        description="Whether the recovered schedule passed independent constraint verification"
    )
    violations: list[str] = Field(
        default_factory=list,
        description="Constraint violations if recovery validation failed"
    )
    wall_time_seconds: float = Field(default=0.0, ge=0.0, description="Time taken to compute recovery in seconds")
    message: str | None = Field(default=None, description="Informative status message")
    statistics: dict[str, Any] = Field(default_factory=dict, description="Solver metrics and change statistics")

    @computed_field
    @property
    def is_success(self) -> bool:
        """Returns True only if the solver found a solution AND independent verification passed."""
        return self.status in (SolverStatus.OPTIMAL, SolverStatus.FEASIBLE) and self.validation_passed

    @computed_field
    @property
    def total_changes(self) -> int:
        """Number of sessions moved or modified."""
        return len(self.changes)


