"""GeCompose: Deterministic Scheduling Engine using Google OR-Tools CP-SAT."""

from gecompose.models import (
    AlternativeSearchResult,
    ConflictConstraint,
    ConflictDiagnosis,
    ConstraintType,
    RelaxationPolicy,
    RelaxedRequirement,
    Room,
    ScheduleAlternative,
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
from gecompose.diagnostics import ConflictDiagnoser, diagnose_conflicts
from gecompose.validator import verify_schedule
from gecompose.exceptions import GeComposeError, ValidationError, SolverError

__all__ = [
    "AlternativeSearchResult",
    "ConflictConstraint",
    "ConflictDiagnosis",
    "ConstraintType",
    "RelaxationPolicy",
    "RelaxedRequirement",
    "Room",
    "ScheduleAlternative",
    "ScheduledAssignment",
    "ScheduleResult",
    "SchedulingProblem",
    "Session",
    "SolverStatus",
    "Teacher",
    "TimeSlot",
    "parse_time_to_minutes",
    "CPSATScheduler",
    "ConflictDiagnoser",
    "solve_schedule",
    "diagnose_conflicts",
    "verify_schedule",
    "GeComposeError",
    "ValidationError",
    "SolverError",
]
