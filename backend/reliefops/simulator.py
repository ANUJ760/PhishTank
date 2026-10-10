"""What-If scenario simulation engine for disaster relief supply allocation."""
from __future__ import annotations

import copy
import time
from typing import Any

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
from backend.reliefops.validator import validate_allocation_plan


class ScenarioSimulator:
    """Simulates counterfactual scenarios without mutating live disaster operational data."""

    def __init__(self, optimizer: AllocationOptimizer | None = None):
        self.optimizer = optimizer or AllocationOptimizer()

    def simulate(
        self,
        baseline_plan: AllocationPlan,
        incident: DisasterIncident,
        camps: list[ReliefCamp],
        resources: list[ResourceType],
        warehouses: list[Warehouse],
        inventory: list[InventoryItem],
        requests: list[ReliefRequest],
        vehicles: list[Vehicle],
        delta: WhatIfDelta,
        scenario_id: str | None = None,
        scenario_name: str = "What-If Simulation",
    ) -> tuple[AllocationPlan, ScenarioComparison]:
        """Apply delta to isolated deep copy of state, run optimizer, and compute comparison."""
        sim_id = scenario_id or f"SIM-{int(time.time())}"

        # Deep-copy everything to guarantee complete isolation from live state
        sim_camps = [copy.deepcopy(c) for c in camps]
        sim_resources = [copy.deepcopy(r) for r in resources]
        sim_warehouses = [copy.deepcopy(w) for w in warehouses]
        sim_inventory = [copy.deepcopy(item) for item in inventory]
        sim_requests = [copy.deepcopy(req) for req in requests]
        sim_vehicles = [copy.deepcopy(v) for v in vehicles]

        # 1. Apply disabled warehouses
        disabled_wh_set = set(delta.disabled_warehouses)
        for w in sim_warehouses:
            if w.id in disabled_wh_set:
                w.is_operational = False

        # 2. Apply disabled vehicles
        disabled_veh_set = set(delta.disabled_vehicles)
        for v in sim_vehicles:
            if v.id in disabled_veh_set:
                v.is_available = False

        # 3. Apply camp access overrides
        for camp in sim_camps:
            if camp.id in delta.camp_access_overrides:
                camp.access_status = delta.camp_access_overrides[camp.id]

        # 4. Apply extra inventory donations / supplies
        if delta.extra_inventory:
            # Find first operational warehouse or fallback
            target_wh_id = next(
                (w.id for w in sim_warehouses if w.is_operational),
                sim_warehouses[0].id if sim_warehouses else "WH-MAIN",
            )
            for res_id, extra_qty in delta.extra_inventory.items():
                if extra_qty <= 0:
                    continue
                # Find matching item or create new
                existing = next(
                    (
                        item
                        for item in sim_inventory
                        if item.warehouse_id == target_wh_id and item.resource_id == res_id
                    ),
                    None,
                )
                if existing:
                    existing.quantity_available += extra_qty
                else:
                    sim_inventory.append(
                        InventoryItem(
                            id=f"EXTRA-{res_id}-{int(time.time())}",
                            warehouse_id=target_wh_id,
                            resource_id=res_id,
                            quantity_available=extra_qty,
                            quantity_reserved=0,
                        )
                    )

        # 5. Apply demand multipliers
        if delta.demand_multipliers:
            for req in sim_requests:
                # Multiplier can be keyed by resource_id or camp_id
                mult = delta.demand_multipliers.get(
                    req.resource_id,
                    delta.demand_multipliers.get(req.camp_id, 1.0),
                )
                if mult != 1.0 and mult > 0:
                    req.quantity_requested = max(1, int(round(req.quantity_requested * mult)))

        # Run optimizer on isolated simulation state
        sim_plan = self.optimizer.solve(
            incident=incident,
            camps=sim_camps,
            resources=sim_resources,
            warehouses=sim_warehouses,
            inventory=sim_inventory,
            requests=sim_requests,
            vehicles=sim_vehicles,
            scenario_id=sim_id,
            scenario_name=scenario_name,
            version=baseline_plan.version + 1,
        )

        # Validate simulated plan
        is_valid, violations = validate_allocation_plan(
            plan=sim_plan,
            camps=sim_camps,
            resources=sim_resources,
            warehouses=sim_warehouses,
            inventory=sim_inventory,
            requests=sim_requests,
            vehicles=sim_vehicles,
        )
        sim_plan.summary.validation_passed = is_valid
        sim_plan.summary.validation_violations = violations

        # Compute side-by-side comparison metrics
        base_summary = baseline_plan.summary
        sim_summary = sim_plan.summary

        fulfillment_diff = round(
            sim_summary.overall_fulfillment_rate - base_summary.overall_fulfillment_rate,
            3,
        )

        allocated_diff: dict[str, int] = {}
        for r_id in set(base_summary.total_allocated.keys()) | set(
            sim_summary.total_allocated.keys()
        ):
            base_alloc = base_summary.total_allocated.get(r_id, 0)
            sim_alloc = sim_summary.total_allocated.get(r_id, 0)
            allocated_diff[r_id] = sim_alloc - base_alloc

        # Compare camp-level allocations
        base_camp_alloc: dict[str, int] = {}
        for a in baseline_plan.allocations:
            base_camp_alloc[a.camp_id] = (
                base_camp_alloc.get(a.camp_id, 0) + a.allocated_quantity
            )

        sim_camp_alloc: dict[str, int] = {}
        for a in sim_plan.allocations:
            sim_camp_alloc[a.camp_id] = (
                sim_camp_alloc.get(a.camp_id, 0) + a.allocated_quantity
            )

        camps_improved: list[str] = []
        camps_degraded: list[str] = []

        all_camp_ids = set(base_camp_alloc.keys()) | set(sim_camp_alloc.keys())
        for c_id in sorted(all_camp_ids):
            b_val = base_camp_alloc.get(c_id, 0)
            s_val = sim_camp_alloc.get(c_id, 0)
            if s_val > b_val:
                camps_improved.append(c_id)
            elif s_val < b_val:
                camps_degraded.append(c_id)

        # Build comparison narrative
        narrative_lines = []
        if fulfillment_diff > 0:
            narrative_lines.append(
                f"Overall supply fulfillment increased by +{fulfillment_diff * 100:.1f}% "
                f"({base_summary.overall_fulfillment_rate * 100:.1f}% -> {sim_summary.overall_fulfillment_rate * 100:.1f}%)."
            )
        elif fulfillment_diff < 0:
            narrative_lines.append(
                f"Overall supply fulfillment decreased by {fulfillment_diff * 100:.1f}% "
                f"({base_summary.overall_fulfillment_rate * 100:.1f}% -> {sim_summary.overall_fulfillment_rate * 100:.1f}%)."
            )
        else:
            narrative_lines.append(
                f"Overall supply fulfillment remained flat at {sim_summary.overall_fulfillment_rate * 100:.1f}%."
            )

        if camps_improved:
            narrative_lines.append(
                f"Benefiting camps ({len(camps_improved)}): {', '.join(camps_improved)}."
            )
        if camps_degraded:
            narrative_lines.append(
                f"Shortage-impacted camps ({len(camps_degraded)}): {', '.join(camps_degraded)}."
            )

        comparison = ScenarioComparison(
            baseline_scenario_id=base_summary.scenario_id,
            simulation_scenario_id=sim_summary.scenario_id,
            delta_applied=delta,
            fulfillment_diff=fulfillment_diff,
            allocated_diff=allocated_diff,
            camps_improved=camps_improved,
            camps_degraded=camps_degraded,
            summary_text=" ".join(narrative_lines),
        )

        return sim_plan, comparison
