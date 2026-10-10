"""GeCompose ReliefOps — Disaster Relief Supply Allocation Engine."""
from __future__ import annotations

from backend.reliefops.audit import AuditRecord, AuditService, compute_plan_hash
from backend.reliefops.explainer import AllocationExplainer, PlanExplanation
from backend.reliefops.intake import RequestIntakeService
from backend.reliefops.models import (
    AllocationPlan,
    CampResourceAllocation,
    DisasterIncident,
    InventoryItem,
    ReliefCamp,
    ReliefRequest,
    ResourceCategory,
    ResourceType,
    ScenarioComparison,
    ScenarioSummary,
    UrgencyLevel,
    Vehicle,
    Warehouse,
    WhatIfDelta,
)
from backend.reliefops.optimizer import AllocationOptimizer
from backend.reliefops.registry import ReliefOpsRegistry, get_reliefops_registry
from backend.reliefops.service import ReliefOpsService, get_reliefops_service
from backend.reliefops.simulator import ScenarioSimulator
from backend.reliefops.validator import AllocationValidationError, validate_allocation_plan

__all__ = [
    "AllocationOptimizer",
    "AllocationPlan",
    "AllocationValidationError",
    "AllocationExplainer",
    "AuditRecord",
    "AuditService",
    "CampResourceAllocation",
    "DisasterIncident",
    "InventoryItem",
    "PlanExplanation",
    "ReliefCamp",
    "ReliefOpsRegistry",
    "ReliefOpsService",
    "ReliefRequest",
    "ResourceCategory",
    "ResourceType",
    "ScenarioComparison",
    "ScenarioSimulator",
    "ScenarioSummary",
    "UrgencyLevel",
    "Vehicle",
    "Warehouse",
    "WhatIfDelta",
    "compute_plan_hash",
    "get_reliefops_registry",
    "get_reliefops_service",
    "validate_allocation_plan",
]
