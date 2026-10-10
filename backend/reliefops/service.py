"""High-level facade service orchestrating GeCompose ReliefOps disaster operations."""
from __future__ import annotations

import logging
from typing import Any

from backend.reliefops.audit import AuditRecord, AuditService, compute_plan_hash
from backend.reliefops.explainer import AllocationExplainer, PlanExplanation
from backend.reliefops.intake import RequestIntakeService
from backend.reliefops.models import (
    AllocationPlan,
    DisasterIncident,
    InventoryItem,
    ReliefCamp,
    ReliefRequest,
    ResourceType,
    ScenarioComparison,
    Vehicle,
    Warehouse,
    WhatIfDelta,
)
from backend.reliefops.optimizer import AllocationOptimizer
from backend.reliefops.registry import ReliefOpsRegistry, get_reliefops_registry
from backend.reliefops.simulator import ScenarioSimulator
from backend.reliefops.validator import validate_allocation_plan

log = logging.getLogger(__name__)


class ReliefOpsService:
    """Production-grade disaster relief coordination and supply allocation engine."""

    def __init__(
        self,
        registry: ReliefOpsRegistry | None = None,
        optimizer: AllocationOptimizer | None = None,
        simulator: ScenarioSimulator | None = None,
        explainer: AllocationExplainer | None = None,
        intake: RequestIntakeService | None = None,
        audit: AuditService | None = None,
    ):
        self.registry = registry or get_reliefops_registry()
        self.optimizer = optimizer or AllocationOptimizer()
        self.simulator = simulator or ScenarioSimulator(self.optimizer)
        self.explainer = explainer or AllocationExplainer()
        self.intake = intake or RequestIntakeService()
        self.audit = audit or AuditService()

    def get_overview(self) -> dict[str, Any]:
        """Return high-level summary of active incident, camps, resources, and latest plan."""
        latest_plan = self.registry.get_latest_plan()
        camps = self.registry.get_camps()
        inventory = self.registry.get_inventory()
        resources = self.registry.get_resources()

        total_pop = sum(c.population for c in camps)
        total_vuln = sum(c.vulnerable_population for c in camps)
        total_items_in_stock = sum(i.quantity_available for i in inventory)

        return {
            "incident": self.registry.incident.model_dump() if self.registry.incident else None,
            "camps_count": len(camps),
            "total_population": total_pop,
            "total_vulnerable_population": total_vuln,
            "warehouses_count": len(self.registry.get_warehouses()),
            "vehicles_count": len(self.registry.get_vehicles()),
            "resources_count": len(resources),
            "pending_requests_count": len(self.registry.get_requests()),
            "total_items_in_stock": total_items_in_stock,
            "has_allocation_plan": latest_plan is not None,
            "latest_plan_id": latest_plan.plan_id if latest_plan else None,
            "latest_plan_approved": latest_plan.approved if latest_plan else False,
            "overall_fulfillment_rate": latest_plan.summary.overall_fulfillment_rate if latest_plan else 0.0,
        }

    def optimize_allocation(
        self,
        scenario_id: str = "SCENARIO-MAIN",
        scenario_name: str = "Baseline CP-SAT Allocation",
    ) -> AllocationPlan:
        """Run CP-SAT solver, validate physical invariants, record audit trail, and persist plan."""
        incident = self.registry.incident or DisasterIncident(
            id="INC-DEFAULT",
            name="Emergency Relief Operation",
            type="flood",
            location="Operational Zone",
        )
        camps = self.registry.get_camps()
        resources = self.registry.get_resources()
        warehouses = self.registry.get_warehouses()
        inventory = self.registry.get_inventory()
        requests = self.registry.get_requests()
        vehicles = self.registry.get_vehicles()

        # Run solver
        plan = self.optimizer.solve(
            incident=incident,
            camps=camps,
            resources=resources,
            warehouses=warehouses,
            inventory=inventory,
            requests=requests,
            vehicles=vehicles,
            scenario_id=scenario_id,
            scenario_name=scenario_name,
        )

        # Independent physical validation
        is_valid, violations = validate_allocation_plan(
            plan=plan,
            camps=camps,
            resources=resources,
            warehouses=warehouses,
            inventory=inventory,
            requests=requests,
            vehicles=vehicles,
        )
        plan.summary.validation_passed = is_valid
        plan.summary.validation_violations = violations

        # Record in audit ledger
        self.audit.record_plan_creation(plan, actor="optimizer", notes="CP-SAT optimization executed")
        self.audit.record_validation(plan, is_valid=is_valid, violations=violations, actor="validator")

        # Save to registry
        self.registry.save_plan(plan)
        return plan

    def run_simulation(
        self,
        delta: WhatIfDelta,
        scenario_id: str | None = None,
        scenario_name: str = "What-If Counterfactual",
    ) -> tuple[AllocationPlan, ScenarioComparison]:
        """Execute what-if simulation against current baseline plan without mutating live state."""
        baseline_plan = self.registry.get_latest_plan()
        if not baseline_plan:
            # Generate baseline plan first
            baseline_plan = self.optimize_allocation()

        sim_plan, comparison = self.simulator.simulate(
            baseline_plan=baseline_plan,
            incident=self.registry.incident,
            camps=self.registry.get_camps(),
            resources=self.registry.get_resources(),
            warehouses=self.registry.get_warehouses(),
            inventory=self.registry.get_inventory(),
            requests=self.registry.get_requests(),
            vehicles=self.registry.get_vehicles(),
            delta=delta,
            scenario_id=scenario_id,
            scenario_name=scenario_name,
        )

        # Record simulation in audit ledger
        self.audit.record_simulation(
            sim_plan=sim_plan,
            baseline_plan_id=baseline_plan.plan_id,
            actor="simulator",
            notes=f"Simulated delta: +{sum(delta.extra_inventory.values())} extra stock, "
                  f"{len(delta.disabled_warehouses)} disabled WH, {len(delta.disabled_vehicles)} disabled vehicles",
        )

        # Also store simulation plan for retrieval
        self.registry.save_plan(sim_plan)
        return sim_plan, comparison

    def explain_plan(self, plan_id: str | None = None) -> PlanExplanation:
        """Generate human-readable AI explanation with Gemma 12B reasoning."""
        plan = self.registry.get_plan(plan_id) if plan_id else self.registry.get_latest_plan()
        if not plan:
            plan = self.optimize_allocation()

        return self.explainer.generate_explanation(
            plan=plan,
            camps=self.registry.get_camps(),
            resources=self.registry.get_resources(),
        )

    def approve_plan(
        self,
        plan_id: str,
        approved_by: str,
        notes: str = "Commander operational sign-off",
    ) -> AuditRecord:
        """Independently validate and authorize an allocation plan for execution."""
        plan = self.registry.get_plan(plan_id)
        if not plan:
            raise LookupError(f"Plan '{plan_id}' not found in registry")

        # Must pass physical validation before approval is permitted
        if not plan.summary.validation_passed:
            raise ValueError(
                f"Cannot approve invalid plan: violations detected ({'; '.join(plan.summary.validation_violations)})"
            )

        record = self.audit.record_approval(plan, approved_by=approved_by, notes=notes)
        return record

    def intake_csv(self, csv_data: str | bytes) -> list[ReliefRequest]:
        """Ingest camp supply requests from CSV."""
        requests = self.intake.parse_csv_requests(
            csv_content=csv_data,
            camps=self.registry.get_camps(),
            resources=self.registry.get_resources(),
        )
        for req in requests:
            self.registry.save_request(req)
        return requests

    def intake_dispatch_report(self, dispatch_text: str) -> list[ReliefRequest]:
        """Ingest unstructured radio/dispatch report using Gemma 4B extraction."""
        requests = self.intake.extract_from_unstructured_text(
            report_text=dispatch_text,
            camps=self.registry.get_camps(),
            resources=self.registry.get_resources(),
        )
        for req in requests:
            self.registry.save_request(req)
        return requests


# Default global service singleton
_relief_service: ReliefOpsService | None = None


def get_reliefops_service() -> ReliefOpsService:
    global _relief_service
    if _relief_service is None:
        _relief_service = ReliefOpsService()
    return _relief_service
