"""Independent allocation validator verifying proposed plans against hard physical invariants."""
from __future__ import annotations

from backend.reliefops.models import (
    AllocationPlan,
    InventoryItem,
    ReliefCamp,
    ReliefRequest,
    ResourceType,
    Vehicle,
    Warehouse,
)


class AllocationValidationError(ValueError):
    """Raised when an allocation violates hard physical invariants."""
    pass


def validate_allocation_plan(
    plan: AllocationPlan,
    camps: list[ReliefCamp],
    resources: list[ResourceType],
    warehouses: list[Warehouse],
    inventory: list[InventoryItem],
    requests: list[ReliefRequest],
    vehicles: list[Vehicle],
) -> tuple[bool, list[str]]:
    """Strictly verify every physical constraint independently from solver logic."""
    violations: list[str] = []

    camp_map = {c.id: c for c in camps}
    res_map = {r.id: r for r in resources}
    req_map = {(r.camp_id, r.resource_id): r for r in requests}

    # 1. Calculate operational inventory per resource
    operational_wh = {w.id for w in warehouses if w.is_operational}
    available_inventory: dict[str, int] = {r.id: 0 for r in resources}
    for item in inventory:
        if item.warehouse_id in operational_wh and item.resource_id in available_inventory:
            available_inventory[item.resource_id] += max(
                0, item.quantity_available - item.quantity_reserved
            )

    # 2. Check total allocated quantities vs inventory limits
    allocated_by_res: dict[str, int] = {r.id: 0 for r in resources}
    for alloc in plan.allocations:
        if alloc.allocated_quantity < 0:
            violations.append(
                f"Negative allocation detected for Camp {alloc.camp_id}, Resource {alloc.resource_id}: {alloc.allocated_quantity}"
            )
        allocated_by_res[alloc.resource_id] = (
            allocated_by_res.get(alloc.resource_id, 0) + alloc.allocated_quantity
        )

    for r_id, total_alloc in allocated_by_res.items():
        max_avail = available_inventory.get(r_id, 0)
        if total_alloc > max_avail:
            violations.append(
                f"Inventory exceeded for {r_id}: allocated {total_alloc} > available {max_avail}"
            )

    # 3. Check requested demand ceilings
    for alloc in plan.allocations:
        req = req_map.get((alloc.camp_id, alloc.resource_id))
        max_req = req.quantity_requested if req else 0
        if alloc.allocated_quantity > max_req:
            violations.append(
                f"Demand ceiling exceeded for Camp {alloc.camp_id}, Resource {alloc.resource_id}: allocated {alloc.allocated_quantity} > requested {max_req}"
            )

    # 4. Check camp storage capacity and weight limits
    camp_volume: dict[str, float] = {c.id: 0.0 for c in camps}
    camp_weight: dict[str, float] = {c.id: 0.0 for c in camps}

    for alloc in plan.allocations:
        res = res_map.get(alloc.resource_id)
        if not res:
            violations.append(f"Unknown resource {alloc.resource_id} in allocation")
            continue
        camp_volume[alloc.camp_id] += alloc.allocated_quantity * res.unit_volume_m3
        camp_weight[alloc.camp_id] += alloc.allocated_quantity * res.unit_weight_kg

    for camp_id, vol in camp_volume.items():
        camp = camp_map.get(camp_id)
        if not camp:
            continue
        if vol > camp.storage_capacity_m3 + 1e-3:
            violations.append(
                f"Storage volume exceeded for {camp.name}: {vol:.2f} m3 > capacity {camp.storage_capacity_m3} m3"
            )

    for camp_id, wt in camp_weight.items():
        camp = camp_map.get(camp_id)
        if not camp:
            continue
        if wt > camp.max_weight_capacity_kg + 1e-3:
            violations.append(
                f"Storage weight exceeded for {camp.name}: {wt:.1f} kg > capacity {camp.max_weight_capacity_kg} kg"
            )

    # 5. Check transportation accessibility
    for camp in camps:
        total_supplies_sent = sum(
            a.allocated_quantity
            for a in plan.allocations
            if a.camp_id == camp.id
        )
        if total_supplies_sent > 0:
            compatible_vehicles = [
                v
                for v in vehicles
                if v.is_available and camp.access_status in v.supported_access
            ]
            if not compatible_vehicles:
                violations.append(
                    f"Camp {camp.name} received supplies ({total_supplies_sent} units) but has NO compatible transport vehicles for access status '{camp.access_status}'"
                )

    is_valid = len(violations) == 0
    return is_valid, violations
