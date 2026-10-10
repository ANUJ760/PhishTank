"""Comprehensive unit and integration test suite for GeCompose ReliefOps Engine."""
from __future__ import annotations

import copy
import pytest
from starlette.testclient import TestClient

from backend.http.app import app
from backend.reliefops import (
    AllocationOptimizer,
    AllocationPlan,
    CampResourceAllocation,
    DisasterIncident,
    InventoryItem,
    PlanExplanation,
    ReliefCamp,
    ReliefOpsRegistry,
    ReliefOpsService,
    ReliefRequest,
    ResourceCategory,
    ResourceType,
    ScenarioComparison,
    UrgencyLevel,
    Vehicle,
    Warehouse,
    WhatIfDelta,
    compute_plan_hash,
    get_reliefops_service,
    validate_allocation_plan,
)


@pytest.fixture
def service() -> ReliefOpsService:
    srv = ReliefOpsService()
    srv.registry.seed_cyclone_disaster_demo()
    return srv


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


# =========================================================================
# 1. CP-SAT Allocation Optimizer Tests
# =========================================================================

def test_optimizer_solves_cyclone_benchmark(service: ReliefOpsService):
    plan = service.optimize_allocation()
    assert plan.summary.solver_status in ("optimal", "feasible")
    assert plan.summary.solve_time_ms >= 0
    assert plan.summary.overall_fulfillment_rate > 0.0
    assert len(plan.allocations) > 0

    # Under benchmark scarcity, critical fulfillment rate should be strictly higher than non-critical
    assert plan.summary.critical_fulfillment_rate >= plan.summary.overall_fulfillment_rate


def test_optimizer_respects_inventory_upper_bound(service: ReliefOpsService):
    plan = service.optimize_allocation()
    summary = plan.summary

    # For every resource, total allocated <= total available
    for r_id, total_alloc in summary.total_allocated.items():
        total_avail = summary.total_available[r_id]
        assert total_alloc <= total_avail, f"Resource {r_id} exceeded available inventory: {total_alloc} > {total_avail}"


def test_optimizer_respects_demand_ceilings(service: ReliefOpsService):
    plan = service.optimize_allocation()

    # For each allocation item, allocated <= requested
    for a in plan.allocations:
        assert a.allocated_quantity <= a.requested_quantity
        assert a.unmet_quantity == a.requested_quantity - a.allocated_quantity
        assert a.allocated_quantity >= 0


def test_optimizer_respects_camp_storage_limits(service: ReliefOpsService):
    plan = service.optimize_allocation()
    camps = service.registry.get_camps()
    camp_map = {c.id: c for c in camps}
    res_map = {r.id: r for r in service.registry.get_resources()}

    for camp in camps:
        camp_allocs = [a for a in plan.allocations if a.camp_id == camp.id]
        tot_vol = sum(a.allocated_quantity * res_map[a.resource_id].unit_volume_m3 for a in camp_allocs)
        tot_wt = sum(a.allocated_quantity * res_map[a.resource_id].unit_weight_kg for a in camp_allocs)

        assert tot_vol <= camp.storage_capacity_m3 + 1e-3
        assert tot_wt <= camp.max_weight_capacity_kg + 1e-3


def test_optimizer_respects_isolated_camp_accessibility(service: ReliefOpsService):
    # Disable the only helicopter (Charlie)
    heli = next((v for v in service.registry.get_vehicles() if v.vehicle_type == "helicopter"), None)
    assert heli is not None
    heli.is_available = False

    plan = service.optimize_allocation()
    # Camp Gamma is air_only, so its allocations should be 0 because no helicopter is available
    gamma_allocs = [a for a in plan.allocations if a.camp_id == "CAMP-GAMMA"]
    assert all(a.allocated_quantity == 0 for a in gamma_allocs)

    # Re-enable helicopter
    heli.is_available = True


# =========================================================================
# 2. Independent Physical Constraint Validator Tests
# =========================================================================

def test_validator_passes_valid_plan(service: ReliefOpsService):
    plan = service.optimize_allocation()
    is_valid, violations = validate_allocation_plan(
        plan=plan,
        camps=service.registry.get_camps(),
        resources=service.registry.get_resources(),
        warehouses=service.registry.get_warehouses(),
        inventory=service.registry.get_inventory(),
        requests=service.registry.get_requests(),
        vehicles=service.registry.get_vehicles(),
    )
    assert is_valid is True
    assert len(violations) == 0


def test_validator_catches_inventory_overdraft(service: ReliefOpsService):
    plan = service.optimize_allocation()
    # Corrupt the plan: inject an extra 100,000 units of water
    corrupted_plan = copy.deepcopy(plan)
    corrupted_plan.allocations[0].allocated_quantity += 100000

    is_valid, violations = validate_allocation_plan(
        plan=corrupted_plan,
        camps=service.registry.get_camps(),
        resources=service.registry.get_resources(),
        warehouses=service.registry.get_warehouses(),
        inventory=service.registry.get_inventory(),
        requests=service.registry.get_requests(),
        vehicles=service.registry.get_vehicles(),
    )
    assert is_valid is False
    assert any("Inventory exceeded" in v for v in violations)


def test_validator_catches_demand_excess(service: ReliefOpsService):
    plan = service.optimize_allocation()
    corrupted_plan = copy.deepcopy(plan)
    # Increase allocation beyond request
    target = corrupted_plan.allocations[0]
    target.allocated_quantity = target.requested_quantity + 50

    is_valid, violations = validate_allocation_plan(
        plan=corrupted_plan,
        camps=service.registry.get_camps(),
        resources=service.registry.get_resources(),
        warehouses=service.registry.get_warehouses(),
        inventory=service.registry.get_inventory(),
        requests=service.registry.get_requests(),
        vehicles=service.registry.get_vehicles(),
    )
    assert is_valid is False
    assert any("Demand ceiling exceeded" in v for v in violations)


def test_validator_catches_negative_allocation(service: ReliefOpsService):
    plan = service.optimize_allocation()
    corrupted_plan = copy.deepcopy(plan)
    corrupted_plan.allocations[0].allocated_quantity = -10

    is_valid, violations = validate_allocation_plan(
        plan=corrupted_plan,
        camps=service.registry.get_camps(),
        resources=service.registry.get_resources(),
        warehouses=service.registry.get_warehouses(),
        inventory=service.registry.get_inventory(),
        requests=service.registry.get_requests(),
        vehicles=service.registry.get_vehicles(),
    )
    assert is_valid is False
    assert any("Negative allocation" in v for v in violations)


# =========================================================================
# 3. What-If Counterfactual Simulator Tests
# =========================================================================

def test_simulator_extra_water_improves_fulfillment(service: ReliefOpsService):
    baseline_plan = service.optimize_allocation()
    base_fulfillment = baseline_plan.summary.overall_fulfillment_rate

    delta = WhatIfDelta(extra_inventory={"WATER_LITERS": 4000})
    sim_plan, comparison = service.run_simulation(delta)

    # Fulfillment should increase
    assert sim_plan.summary.overall_fulfillment_rate > base_fulfillment
    assert comparison.fulfillment_diff > 0
    assert comparison.allocated_diff["WATER_LITERS"] > 0
    assert len(comparison.camps_improved) > 0
    assert "increased" in comparison.summary_text.lower()


def test_simulator_disabled_warehouse_reduces_fulfillment(service: ReliefOpsService):
    baseline_plan = service.optimize_allocation()
    base_fulfillment = baseline_plan.summary.overall_fulfillment_rate

    # Disabling central warehouse should reduce stock severely
    delta = WhatIfDelta(disabled_warehouses=["WH-CENTRAL"])
    sim_plan, comparison = service.run_simulation(delta)

    assert sim_plan.summary.overall_fulfillment_rate < base_fulfillment
    assert comparison.fulfillment_diff < 0
    assert len(comparison.camps_degraded) > 0


def test_simulator_preserves_live_inventory_isolation(service: ReliefOpsService):
    # Live inventory before simulation
    inv_before = {item.id: item.quantity_available for item in service.registry.get_inventory()}

    delta = WhatIfDelta(extra_inventory={"WATER_LITERS": 10000}, disabled_warehouses=["WH-PORT"])
    service.run_simulation(delta)

    # Live inventory must remain completely unchanged
    inv_after = {item.id: item.quantity_available for item in service.registry.get_inventory()}
    assert inv_before == inv_after

    wh_port = service.registry.warehouses.get("WH-PORT")
    assert wh_port is not None
    assert wh_port.is_operational is True


# =========================================================================
# 4. Request Intake Service Tests
# =========================================================================

def test_intake_csv_requests(service: ReliefOpsService):
    csv_text = """camp_id,resource_id,quantity_requested,urgency,evidence_notes
CAMP-ALPHA,WATER_LITERS,500,CRITICAL,Flood waters cut local borehole
CAMP-BETA,FOOD_RATIONS,300,HIGH,Food storage spoiled by cyclone
CAMP-DELTA,BLANKETS,150,MEDIUM,Temporary emergency shelter intake
"""
    reqs = service.intake_csv(csv_text)
    assert len(reqs) == 3
    assert reqs[0].camp_id == "CAMP-ALPHA"
    assert reqs[0].resource_id == "WATER_LITERS"
    assert reqs[0].quantity_requested == 500
    assert reqs[0].urgency == UrgencyLevel.CRITICAL


def test_intake_unstructured_text_heuristic(service: ReliefOpsService, monkeypatch):
    # Force heuristic path for deterministic unit test
    import backend.config as cfg
    monkeypatch.setattr(cfg, "MOCK_LLM", True)

    dispatch_report = (
        "Radio Dispatch from Camp Alpha: Urgent distress! We have critical water shortage. "
        "Need 1500 liters of water and 600 food packets immediately!"
    )
    reqs = service.intake_dispatch_report(dispatch_report)
    assert len(reqs) >= 1
    water_req = next((r for r in reqs if r.resource_id == "WATER_LITERS"), None)
    assert water_req is not None
    assert water_req.quantity_requested == 1500
    assert water_req.urgency == UrgencyLevel.CRITICAL


# =========================================================================
# 5. Explainer and Audit Ledger Tests
# =========================================================================

def test_explainer_generates_transparent_rationale(service: ReliefOpsService, monkeypatch):
    import backend.config as cfg
    monkeypatch.setattr(cfg, "MOCK_LLM", True)

    plan = service.optimize_allocation()
    explanation = service.explain_plan(plan.plan_id)

    assert isinstance(explanation, PlanExplanation)
    assert len(explanation.overview) > 0
    assert len(explanation.key_findings) > 0
    assert len(explanation.bottleneck_resources) > 0
    assert len(explanation.camp_explanations) == len(service.registry.get_camps())


def test_audit_ledger_cryptographic_chain(service: ReliefOpsService):
    plan = service.optimize_allocation()
    plan_hash = compute_plan_hash(plan)
    assert len(plan_hash) == 64  # SHA-256 length

    # Approve plan
    approval_rec = service.approve_plan(
        plan_id=plan.plan_id,
        approved_by="Col. S. Rao, District Disaster Controller",
        notes="Authorized for immediate multi-modal transport dispatch",
    )
    assert approval_rec.event_type == "PLAN_APPROVED"
    assert plan.approved is True

    # Verify audit chain integrity
    is_valid, msg = service.audit.verify_chain_integrity()
    assert is_valid is True
    assert "verified" in msg.lower()


def test_audit_prevent_approval_of_invalid_plan(service: ReliefOpsService):
    plan = service.optimize_allocation()
    # Mark plan invalid
    plan.summary.validation_passed = False
    plan.summary.validation_violations = ["Simulated violation: structural weight exceeded"]

    with pytest.raises(ValueError, match="Cannot approve invalid plan"):
        service.approve_plan(plan.plan_id, approved_by="Commander")


# =========================================================================
# 6. REST API Endpoints Tests
# =========================================================================

def test_api_reliefops_overview(client: TestClient):
    resp = client.get("/api/v1/reliefops/overview")
    assert resp.status_code == 200
    data = resp.json()
    assert data["camps_count"] == 4
    assert data["total_population"] == 7650
    assert data["warehouses_count"] == 2
    assert data["vehicles_count"] == 4
    assert data["resources_count"] == 5


def test_api_reliefops_camps(client: TestClient):
    resp = client.get("/api/v1/reliefops/camps")
    assert resp.status_code == 200
    camps = resp.json()
    assert len(camps) == 4
    assert any(c["id"] == "CAMP-BETA" and c["access_status"] == "boat_only" for c in camps)


def test_api_reliefops_optimize_and_retrieve(client: TestClient):
    resp = client.post("/api/v1/reliefops/optimize", json={"scenario_name": "API Test Run"})
    assert resp.status_code == 200
    plan = resp.json()
    assert plan["summary"]["solver_status"] in ("optimal", "feasible")
    assert len(plan["allocations"]) > 0

    plan_id = plan["plan_id"]
    get_resp = client.get(f"/api/v1/reliefops/plan/{plan_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["plan_id"] == plan_id


def test_api_reliefops_simulate(client: TestClient):
    # Seed baseline
    client.post("/api/v1/reliefops/optimize")

    sim_payload = {
        "delta": {"extra_inventory": {"WATER_LITERS": 5000}},
        "scenario_name": "Donation Influx Simulation",
    }
    resp = client.post("/api/v1/reliefops/simulate", json=sim_payload)
    assert resp.status_code == 200
    body = resp.json()
    assert "simulation_plan" in body
    assert "comparison" in body
    assert body["comparison"]["fulfillment_diff"] > 0


def test_api_reliefops_approve_and_audit(client: TestClient):
    opt_resp = client.post("/api/v1/reliefops/optimize")
    plan_id = opt_resp.json()["plan_id"]

    approve_payload = {
        "plan_id": plan_id,
        "approved_by": "State Disaster Command",
        "notes": "Fast-tracked for morning convoy",
    }
    app_resp = client.post("/api/v1/reliefops/approve", json=approve_payload)
    assert app_resp.status_code == 200
    assert app_resp.json()["event_type"] == "PLAN_APPROVED"

    audit_resp = client.get("/api/v1/reliefops/audit")
    assert audit_resp.status_code == 200
    audit_data = audit_resp.json()
    assert audit_data["verified"] is True
    assert len(audit_data["records"]) >= 3
