"""Domain-agnostic universal constraint optimization models."""
from __future__ import annotations

from enum import Enum, IntEnum
import time
from typing import Any
from pydantic import BaseModel, Field


class ConstraintPriority(IntEnum):
    """Urgency / Priority weights for universal tasks."""
    CRITICAL_EMERGENCY = 1
    HIGH_PRIORITY = 2
    NORMAL = 3
    LOW_BACKGROUND = 4


class ResourceKind(str, Enum):
    SPACE = "space"           # Room, Operating Theatre, Warehouse, Bay
    HUMAN = "human"           # Surgeon, Specialist, Driver, Instructor
    EQUIPMENT = "equipment"   # Medical device, Heavy vehicle, Machine
    INVENTORY = "inventory"   # Sterile kit, Consumable, Fuel


class UniversalResource(BaseModel):
    """A physical, human, or logistical resource with capabilities and availability."""
    id: str
    name: str
    kind: ResourceKind
    capabilities: list[str] = Field(default_factory=list)  # e.g. ["cardiac", "laminar_flow", "icu"]
    capacity: int = 1                                      # Max parallel tasks or units
    is_operational: bool = True
    turnaround_minutes: int = 0                            # Mandatory cleaning / cooling / setup delay
    available_intervals: list[tuple[int, int]] = Field(default_factory=list)  # (start, end) minutes
    metadata: dict[str, Any] = Field(default_factory=dict)


class UniversalTask(BaseModel):
    """A unit of work requiring resources within an operational time window."""
    id: str
    name: str
    priority: ConstraintPriority = ConstraintPriority.NORMAL
    duration_minutes: int
    earliest_start_minute: int = 0
    deadline_minute: int | None = None
    required_capabilities: list[str] = Field(default_factory=list)  # Capabilities required from space/human
    required_resource_kinds: list[ResourceKind] = Field(default_factory=list)
    precedence_task_ids: list[str] = Field(default_factory=list)    # Must finish before this starts
    evidence_notes: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)


class UniversalAssignment(BaseModel):
    """Assignment of a task to resources and a time window."""
    task_id: str
    task_name: str
    priority: str
    assigned_resource_ids: list[str]
    start_minute: int
    end_minute: int
    turnaround_end_minute: int
    delay_minutes: int
    is_on_time: bool
    rationale: str


class UniversalProblem(BaseModel):
    """Domain-agnostic specification of a constraint optimization problem."""
    problem_id: str
    domain: str  # e.g., "hospital_surgery", "disaster_logistics", "datacenter_jobs"
    horizon_minutes: int = 1440  # 24 hours standard
    resources: list[UniversalResource]
    tasks: list[UniversalTask]
    created_at: float = Field(default_factory=time.time)


class UniversalSolution(BaseModel):
    """Output solution of the universal CP-SAT solver."""
    solution_id: str
    problem_id: str
    domain: str
    solver_status: str  # optimal, feasible, infeasible
    solve_time_ms: int
    total_tasks: int
    scheduled_tasks: int
    unmet_tasks: int
    overall_fulfillment_rate: float
    critical_fulfillment_rate: float
    assignments: list[UniversalAssignment]
    unmet_task_ids: list[str] = Field(default_factory=list)
    validation_passed: bool = True
    validation_violations: list[str] = Field(default_factory=list)
    solution_hash: str = ""
    created_at: float = Field(default_factory=time.time)
