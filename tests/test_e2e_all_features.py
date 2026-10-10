"""
Comprehensive End-to-End Verification of All GeCompose Subsystems and Features
"""
import os
import sys
import pytest

os.environ["MOCK_LLM"] = "1"

from backend import api
from backend.models import Roster, Rule
from backend.registry import db
from backend.ledger import ledger
from backend.reliefops import get_reliefops_service, WhatIfDelta
from backend.medops import get_medops_service
from backend.universal import (
    UniversalProblem,
    UniversalResource,
    UniversalTask,
    UniversalConstraintSolver,
    ResourceKind,
    ConstraintPriority,
)
from gecompose.investigation_models import (
    Incident, Evidence, EvidenceLink, EvidenceRelationshipType, EvidenceSourceType, Hypothesis, HypothesisStatus
)
from gecompose.investigation import evaluate_hypothesis


def test_comprehensive_e2e_all_subsystems():
    # 1. Database & Demo Reset
    api.reset_demo()
    api.seed_demo()
    roster = api.get_roster()
    assert len(roster.teachers) > 0, "Roster teachers should not be empty"

    # 2. Rule Management
    rules = api.list_rules()
    assert len(rules) >= 2, "Seeded rules should be present"

    # 3. Constraint Solver & Feasibility
    solve_res = api.solve(minimal_change=True)
    assert solve_res.status == "feasible", f"Expected feasible schedule, got {solve_res.status}"
    assert solve_res.schedule is not None
    assert len(solve_res.schedule.placements) > 0

    # 4. Publication, Hashes & Verification
    pub_res = api.publish()
    assert pub_res.hash
    assert pub_res.json_bytes
    verify_res = api.verify_file(pub_res.json_bytes)
    assert verify_res.match is True
    assert verify_res.anchored is True

    # 5. Tamper-Proof Cryptographic Ledger
    events = api.ledger_events()
    assert len(events) > 0
    integrity = api.verify_ledger()
    assert integrity["verified"] is True
    assert integrity["valid"] is True

    # 6. Conflict Diagnosis & Relaxation Explanation
    conflicting_rule = Rule(
        id="R_CONFLICT_TEST",
        type="pin_session",
        owner="Dean",
        params={"session_id": "DB_LAB", "day": 1, "slots": [0, 1, 2]},
        status="draft"
    )
    db.save_rule(conflicting_rule)
    api.confirm_rule("R_CONFLICT_TEST")
    conflict_res = api.solve(minimal_change=False)
    if conflict_res.conflict:
        explanation = api.explain_conflict(conflict_res.conflict)
        assert explanation is not None
    api.reset_demo()
    api.seed_demo()

    # 7. ReliefOps Disaster Supply Allocation
    relief_svc = get_reliefops_service()
    relief_overview = relief_svc.get_overview()
    assert relief_overview["camps_count"] > 0
    assert relief_overview["total_items_in_stock"] > 0
    relief_plan = relief_svc.optimize_allocation("Disaster Test Scenario")
    assert relief_plan.summary.solver_status.lower() in ("optimal", "feasible")
    assert relief_plan.summary.validation_passed is True
    assert len(relief_plan.allocations) > 0

    sim_plan, comparison = relief_svc.run_simulation(
        delta=WhatIfDelta(additional_inventory={"RES-WATER": 500}),
        scenario_name="Additional Water Simulation"
    )
    assert comparison is not None

    # 8. MedOps Hospital Operating Room Allocation
    med_svc = get_medops_service()
    med_overview = med_svc.get_overview()
    assert med_overview["operating_rooms_count"] > 0
    assert med_overview["total_patient_cases"] > 0
    med_plan = med_svc.optimize_schedule("Emergency OR Shift")
    assert med_plan.summary.solver_status.lower() in ("optimal", "feasible")
    assert med_plan.summary.validation_passed is True
    assert med_plan.summary.scheduled_cases > 0

    # 9. Universal Constraint Solver
    problem = UniversalProblem(
        problem_id="UNIV-TEST",
        domain="datacenter_scheduling",
        resources=[UniversalResource(id="NODE-1", name="Compute Node 1", kind=ResourceKind.SPACE, capacity=1)],
        tasks=[
            UniversalTask(id="TASK-1", name="Data Ingestion", priority=ConstraintPriority.HIGH_PRIORITY, duration_minutes=60),
            UniversalTask(id="TASK-2", name="Model Training", priority=ConstraintPriority.HIGH_PRIORITY, duration_minutes=120, precedence_task_ids=["TASK-1"]),
        ],
    )
    solver = UniversalConstraintSolver()
    univ_solution = solver.solve(problem)
    assert univ_solution.solver_status in ("optimal", "feasible")

    # 10. Incident Investigation Engine
    incident = Incident(
        id="INC-001",
        title="Warehouse Inventory Discrepancy",
        description="Supply discrepancy reported at Warehouse Alpha during cyclone response",
        affected_component="warehouse-alpha",
    )
    ev = Evidence(
        id="EV-1",
        source_type=EvidenceSourceType.LOGS,
        summary="Intake gate logs show truck arrival 2 hours before system manifest entry",
        reliability=0.95
    )
    hyp = Hypothesis(
        id="H-1",
        title="Delayed Intake Digitization",
        description="Shipments arrived physically but intake manifests were not yet digitized",
        evidence_links=[EvidenceLink(evidence_id="EV-1", relationship=EvidenceRelationshipType.SUPPORTS)]
    )
    evaluated = evaluate_hypothesis(hyp, {"EV-1": ev})
    assert evaluated.status in (HypothesisStatus.PLAUSIBLE, HypothesisStatus.STRONGLY_SUPPORTED)

    # 11. Scoreboard Robustness
    scoreboard_res = api.run_scoreboard(runs=2)
    assert len(scoreboard_res.rows) == 2
    for r in scoreboard_res.rows:
        assert r.gecompose_violations == 0
