"""Universal domain-agnostic constraint satisfaction and optimization engine."""
from __future__ import annotations

from backend.universal.models import (
    ConstraintPriority,
    ResourceKind,
    UniversalAssignment,
    UniversalProblem,
    UniversalResource,
    UniversalSolution,
    UniversalTask,
)
from backend.universal.solver import UniversalConstraintSolver

__all__ = [
    "ConstraintPriority",
    "ResourceKind",
    "UniversalAssignment",
    "UniversalConstraintSolver",
    "UniversalProblem",
    "UniversalResource",
    "UniversalSolution",
    "UniversalTask",
]
