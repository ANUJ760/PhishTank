"""GeCompose: Deterministic Scheduling Engine using Google OR-Tools CP-SAT."""

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
from gecompose.solver import CPSATScheduler, solve_schedule
from gecompose.validator import verify_schedule
from gecompose.exceptions import GeComposeError, ValidationError, SolverError

__all__ = [
    "Room",
    "ScheduledAssignment",
    "ScheduleResult",
    "SchedulingProblem",
    "Session",
    "SolverStatus",
    "Teacher",
    "TimeSlot",
    "parse_time_to_minutes",
    "CPSATScheduler",
    "solve_schedule",
    "verify_schedule",
    "GeComposeError",
    "ValidationError",
    "SolverError",
]
