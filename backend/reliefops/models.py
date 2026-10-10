"""Strongly-typed domain models for GeCompose ReliefOps Supply Allocation Engine."""
from __future__ import annotations

from enum import Enum, IntEnum
import time
from typing import Any
from pydantic import BaseModel, Field


class UrgencyLevel(IntEnum):
    """Urgency level for relief supply requests; lower int = higher urgency."""
    CRITICAL = 1
    HIGH = 2
    MEDIUM = 3
    LOW = 4


class ResourceCategory(str, Enum):
    SURVIVAL = "survival"
    MEDICAL = "medical"
    FOOD = "food"
    SHELTER = "shelter"
    POWER = "power"
    HYGIENE = "hygiene"


class DisasterIncident(BaseModel):
    id: str
    name: str
    type: str  # e.g., "cyclone", "flood", "earthquake"
    location: str
    severity: str = "critical"  # critical, severe, moderate
    created_at: float = Field(default_factory=time.time)


class ReliefCamp(BaseModel):
    id: str
    incident_id: str
    name: str
    location: str
    population: int
    vulnerable_population: int = 0  # children, elderly, injured
    storage_capacity_m3: float = 100.0  # max storage volume in cubic meters
    max_weight_capacity_kg: float = 20000.0  # max structural storage weight
    access_status: str = "open"  # open, restricted_road, air_only, boat_only
    contact_person: str = "Camp Coordinator"


class ResourceType(BaseModel):
    id: str  # e.g., "WATER_LITERS", "FOOD_RATIONS", "BLANKETS", "MEDICAL_KITS"
    name: str
    unit: str  # liters, packets, kits, pieces
    category: ResourceCategory
    unit_weight_kg: float = 1.0
    unit_volume_m3: float = 0.005
    priority_weight: int = 10  # higher weight = higher allocation priority
    is_perishable: bool = False


class Warehouse(BaseModel):
    id: str
    name: str
    location: str
    is_operational: bool = True
    total_capacity_m3: float = 500.0


class InventoryItem(BaseModel):
    id: str
    warehouse_id: str
    resource_id: str
    quantity_available: int
    quantity_reserved: int = 0


class Vehicle(BaseModel):
    id: str
    name: str
    vehicle_type: str = "heavy_truck"  # heavy_truck, light_truck, helicopter, boat
    max_weight_kg: float = 10000.0
    max_volume_m3: float = 40.0
    is_available: bool = True
    supported_access: list[str] = Field(default_factory=lambda: ["open", "restricted_road"])


class ReliefRequest(BaseModel):
    id: str
    camp_id: str
    resource_id: str
    quantity_requested: int
    urgency: UrgencyLevel = UrgencyLevel.HIGH
    evidence_notes: str = ""
    evidence_ref: str = ""
    status: str = "pending"  # pending, approved, fulfilled, partially_fulfilled
    created_at: float = Field(default_factory=time.time)


class CampResourceAllocation(BaseModel):
    camp_id: str
    camp_name: str
    resource_id: str
    resource_name: str
    requested_quantity: int
    allocated_quantity: int
    unmet_quantity: int
    fulfillment_ratio: float
    priority_classification: str
    allocation_rationale: str
    relevant_constraints: list[str] = Field(default_factory=list)
    shipment_details: dict[str, Any] = Field(default_factory=dict)


class ScenarioSummary(BaseModel):
    scenario_id: str
    name: str
    solver_status: str  # optimal, feasible, infeasible
    solve_time_ms: int
    total_requested: dict[str, int]
    total_available: dict[str, int]
    total_allocated: dict[str, int]
    total_unmet: dict[str, int]
    overall_fulfillment_rate: float
    critical_fulfillment_rate: float
    fairness_index: float  # minimum fulfillment across camps (maximin fairness)
    weighted_unmet_demand: float
    validation_passed: bool
    validation_violations: list[str] = Field(default_factory=list)
    unresolved_shortages: list[dict[str, Any]] = Field(default_factory=list)
    created_at: float = Field(default_factory=time.time)


class AllocationPlan(BaseModel):
    plan_id: str
    incident_id: str
    version: int = 1
    summary: ScenarioSummary
    allocations: list[CampResourceAllocation]
    approved: bool = False
    approved_by: str | None = None
    plan_hash: str = ""
    created_at: float = Field(default_factory=time.time)


class WhatIfDelta(BaseModel):
    extra_inventory: dict[str, int] = Field(default_factory=dict)
    disabled_warehouses: list[str] = Field(default_factory=list)
    disabled_vehicles: list[str] = Field(default_factory=list)
    demand_multipliers: dict[str, float] = Field(default_factory=dict)
    camp_access_overrides: dict[str, str] = Field(default_factory=dict)


class ScenarioComparison(BaseModel):
    baseline_scenario_id: str
    simulation_scenario_id: str
    delta_applied: WhatIfDelta
    fulfillment_diff: float
    allocated_diff: dict[str, int]
    camps_improved: list[str]
    camps_degraded: list[str]
    summary_text: str
