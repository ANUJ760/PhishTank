"""Comprehensive unit and integration test suite for MedOps Hospital Operating Theatres and Universal Constraint Solver."""
from __future__ import annotations

import copy
import pytest
from starlette.testclient import TestClient

from backend.http.app import app
from backend.medops import (
    HospitalORPlan,
    HospitalPlanExplanation,
    MedOpsService,
    OperatingRoom,
    PatientCase,
    SurgicalScheduleItem,
    SurgicalSpecialty,
    TriageUrgency,
    WhatIfHospitalDelta,
    compute_hospital_plan_hash,
    get_medops_service,
    validate_hospital_plan,
)
from backend.universal import (
    ConstraintPriority,
    ResourceKind,
    UniversalConstraintSolver,
    UniversalProblem,
    UniversalResource,
    UniversalTask,
)


@pytest.fixture
def service() -> MedOpsService:
    srv = MedOpsService()
    srv.registry.seed_level1_trauma_benchmark()
    return srv


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


# =========================================================================
# 1. Universal Domain-Agnostic Constraint Solver Tests
# =========================================================================

def test_universal_solver_precedence():
    problem = UniversalProblem(
        problem_id="UNIV-PREC",
        domain="datacenter_pipelines",
        resources=[
            UniversalResource(id="NODE-1", name="Compute Node 1", kind=ResourceKind.SPACE, capacity=1),
        ],
        tasks=[
            UniversalTask(id="TASK-1", name="Data Ingestion", priority=ConstraintPriority.HIGH_PRIORITY, duration_minutes=60),
            UniversalTask(id="TASK-2", name="Model Training", priority=ConstraintPriority.HIGH_PRIORITY, duration_minutes=120, precedence_task_ids=["TASK-1"]),
        ],
    )
    solver = UniversalConstraintSolver()
    solution = solver.solve(problem)

    assert solution.solver_status in ("optimal", "feasible")
    assert solution.scheduled_tasks == 2

    t1 = next(a for a in solution.assignments if a.task_id == "TASK-1")
    t2 = next(a for a in solution.assignments if a.task_id == "TASK-2")
    assert t2.start_minute >= t1.end_minute


def test_universal_solver_turnaround_enforced():
    problem = UniversalProblem(
        problem_id="UNIV-TURN",
        domain="flight_gates",
        resources=[
            UniversalResource(id="GATE-A", name="Terminal Gate A", kind=ResourceKind.SPACE, capacity=1, turnaround_minutes=45),
        ],
        tasks=[
            UniversalTask(id="FLIGHT-1", name="Inbound Flight 101", priority=ConstraintPriority.NORMAL, duration_minutes=60),
            UniversalTask(id="FLIGHT-2", name="Inbound Flight 102", priority=ConstraintPriority.NORMAL, duration_minutes=60),
        ],
    )
    solver = UniversalConstraintSolver()
    solution = solver.solve(problem)

    assert solution.scheduled_tasks == 2
    f1 = next(a for a in solution.assignments if a.task_id == "FLIGHT-1")
    f2 = next(a for a in solution.assignments if a.task_id == "FLIGHT-2")

    first, second = (f1, f2) if f1.start_minute < f2.start_minute else (f2, f1)
    assert second.start_minute >= first.end_minute + 45


# =========================================================================
# 2. MedOps Hospital Surgical Optimizer Tests
# =========================================================================

def test_medops_solves_level1_trauma_benchmark(service: MedOpsService):
    plan = service.optimize_schedule()
    assert plan.summary.solver_status in ("optimal", "feasible")
    assert plan.summary.scheduled_cases > 0
    assert plan.summary.resuscitation_l1_fulfillment == 1.0
    assert len(plan.items) > 0


def test_medops_enforces_sterilization_clearance(service: MedOpsService):
    plan = service.optimize_schedule()
    rooms = service.registry.get_rooms()
    room_map = {r.id: r for r in rooms}

    # Group by room
    by_room: dict[str, list] = {}
    for item in plan.items:
        by_room.setdefault(item.or_room_id, []).append(item)

    for r_id, items in by_room.items():
        room = room_map[r_id]
        sorted_items = sorted(items, key=lambda x: x.start_minute)
        for i in range(len(sorted_items) - 1):
            curr = sorted_items[i]
            nxt = sorted_items[i + 1]
            required_clearance = curr.end_minute + room.turnaround_sterilization_minutes
            assert nxt.start_minute >= required_clearance, (
                f"Sterilization violated in {room.name}: {nxt.start_minute} < {required_clearance}"
            )


def test_medops_surgeon_non_overlap(service: MedOpsService):
    plan = service.optimize_schedule()
    by_surg: dict[str, list] = {}
    for item in plan.items:
        by_surg.setdefault(item.lead_surgeon_id, []).append(item)

    for surg_id, items in by_surg.items():
        sorted_items = sorted(items, key=lambda x: x.start_minute)
        for i in range(len(sorted_items) - 1):
            curr = sorted_items[i]
            nxt = sorted_items[i + 1]
            assert nxt.start_minute >= curr.end_minute, (
                f"Surgeon {surg_id} double-booked: {nxt.start_minute} < {curr.end_minute}"
            )


def test_medops_equipment_matching(service: MedOpsService):
    plan = service.optimize_schedule()
    cardiac_case = next((i for i in plan.items if i.specialty == "cardiac"), None)
    if cardiac_case:
        # Must be in cardiac suite equipped with cardiopulmonary bypass
        room = next(r for r in service.registry.get_rooms() if r.id == cardiac_case.or_room_id)
        assert "cardiopulmonary_bypass" in room.equipped_capabilities


# =========================================================================
# 3. Independent Clinical Validator Tests
# =========================================================================

def test_validator_passes_valid_plan(service: MedOpsService):
    plan = service.optimize_schedule()
    is_valid, violations = validate_hospital_plan(
        plan=plan,
        operating_rooms=service.registry.get_rooms(),
        staff=service.registry.get_staff(),
        patient_cases=service.registry.get_cases(),
        icu_bed_capacity=service.registry.icu_bed_capacity,
    )
    assert is_valid is True
    assert len(violations) == 0


def test_validator_catches_room_double_booking(service: MedOpsService):
    plan = service.optimize_schedule()
    corrupted = copy.deepcopy(plan)
    # Force two cases to overlap in the same room
    if len(corrupted.items) >= 2:
        corrupted.items[1].or_room_id = corrupted.items[0].or_room_id
        corrupted.items[1].start_minute = corrupted.items[0].start_minute + 10
        corrupted.items[1].end_minute = corrupted.items[0].end_minute + 10

        is_valid, violations = validate_hospital_plan(
            plan=corrupted,
            operating_rooms=service.registry.get_rooms(),
            staff=service.registry.get_staff(),
            patient_cases=service.registry.get_cases(),
        )
        assert is_valid is False
        assert any("DOUBLE-BOOKING" in v or "STERILITY" in v for v in violations)


def test_validator_catches_surgeon_double_booking(service: MedOpsService):
    plan = service.optimize_schedule()
    corrupted = copy.deepcopy(plan)
    if len(corrupted.items) >= 2:
        # Put same surgeon on different rooms at the same time
        corrupted.items[1].lead_surgeon_id = corrupted.items[0].lead_surgeon_id
        corrupted.items[1].or_room_id = "OR-GENERAL-SUITE"
        corrupted.items[0].or_room_id = "OR-TRAUMA-HYBRID"
        corrupted.items[1].start_minute = corrupted.items[0].start_minute
        corrupted.items[1].end_minute = corrupted.items[0].end_minute

        is_valid, violations = validate_hospital_plan(
            plan=corrupted,
            operating_rooms=service.registry.get_rooms(),
            staff=service.registry.get_staff(),
            patient_cases=service.registry.get_cases(),
        )
        assert is_valid is False
        assert any("CLINICAL STAFF OVERLAP" in v for v in violations)


# =========================================================================
# 4. What-If Scenario Simulator Tests
# =========================================================================

def test_simulator_mass_casualty_surge(service: MedOpsService):
    baseline_plan = service.optimize_schedule()

    delta = WhatIfHospitalDelta(
        mass_casualty_cases=[
            PatientCase(
                id="SURGE-MCI-1",
                mrn="MRN-MCI-01",
                patient_name="Multi-Casualty Trauma #1",
                age=31,
                triage_urgency=TriageUrgency.RESUSCITATION_L1,
                specialty=SurgicalSpecialty.TRAUMA,
                estimated_duration_minutes=120,
                arrival_minute=30,
            ),
            PatientCase(
                id="SURGE-MCI-2",
                mrn="MRN-MCI-02",
                patient_name="Multi-Casualty Trauma #2",
                age=44,
                triage_urgency=TriageUrgency.RESUSCITATION_L1,
                specialty=SurgicalSpecialty.TRAUMA,
                estimated_duration_minutes=90,
                arrival_minute=45,
            ),
        ]
    )
    sim_plan, comparison = service.run_simulation(delta)

    assert sim_plan.summary.solver_status in ("optimal", "feasible")
    assert comparison.simulation_plan_id == sim_plan.plan_id
    assert "Surge of 2 mass-casualty emergency patient(s)" in comparison.summary_text


def test_simulator_or_room_decontamination_closure(service: MedOpsService):
    baseline_plan = service.optimize_schedule()

    # Close Trauma Hybrid OR
    delta = WhatIfHospitalDelta(
        decontaminated_or_rooms=["OR-TRAUMA-HYBRID"],
    )
    sim_plan, comparison = service.run_simulation(delta)

    # In simulated plan, no case should be scheduled in OR-TRAUMA-HYBRID
    assert all(item.or_room_id != "OR-TRAUMA-HYBRID" for item in sim_plan.items)
    assert "Decontamination offline status applied" in comparison.summary_text


def test_simulator_preserves_live_registry_isolation(service: MedOpsService):
    cases_count_before = len(service.registry.get_cases())

    delta = WhatIfHospitalDelta(
        mass_casualty_cases=[
            PatientCase(
                id="SURGE-TEMP-1",
                mrn="MRN-TEMP",
                patient_name="Temporary Case",
                age=50,
                triage_urgency=TriageUrgency.RESUSCITATION_L1,
                specialty=SurgicalSpecialty.TRAUMA,
                estimated_duration_minutes=60,
            )
        ],
        decontaminated_or_rooms=["OR-CARDIAC-SUITE"],
    )
    service.run_simulation(delta)

    # Live registry must remain completely unmodified
    assert len(service.registry.get_cases()) == cases_count_before
    room_cardiac = next(r for r in service.registry.get_rooms() if r.id == "OR-CARDIAC-SUITE")
    assert room_cardiac.is_operational is True


# =========================================================================
# 5. Request Intake Service Tests
# =========================================================================

def test_medops_intake_csv_cases(service: MedOpsService):
    csv_text = """mrn,name,age,specialty,triage,duration,arrival
MRN-5501,James Cole,42,trauma,RESUSCITATION_L1,90,0
MRN-5502,Alice Gray,29,general,EMERGENT_L2,60,30
MRN-5503,Peter Pan,55,orthopedic,ELECTIVE_L4,120,180
"""
    cases = service.intake_csv(csv_text)
    assert len(cases) == 3
    assert cases[0].triage_urgency == TriageUrgency.RESUSCITATION_L1
    assert cases[0].specialty == SurgicalSpecialty.TRAUMA
    assert cases[1].triage_urgency == TriageUrgency.EMERGENT_L2


def test_medops_intake_dispatch_heuristic(service: MedOpsService, monkeypatch):
    import backend.config as cfg
    monkeypatch.setattr(cfg, "MOCK_LLM", True)

    dispatch_call = (
        "Inbound Paramedic Radio: High speed rollover, 24yo male with penetrating chest trauma "
        "and cardiac tamponade. Massive active hemorrhage, requires immediate cardiac bypass and resuscitation!"
    )
    cases = service.intake_dispatch(dispatch_call)
    assert len(cases) >= 1
    assert cases[0].triage_urgency == TriageUrgency.RESUSCITATION_L1
    assert cases[0].specialty == SurgicalSpecialty.CARDIAC


# =========================================================================
# 6. Explainer and Cryptographic Audit Tests
# =========================================================================

def test_medops_explainer_clinical_rationale(service: MedOpsService, monkeypatch):
    import backend.config as cfg
    monkeypatch.setattr(cfg, "MOCK_LLM", True)

    plan = service.optimize_schedule()
    explanation = service.explain_schedule(plan.plan_id)

    assert isinstance(explanation, HospitalPlanExplanation)
    assert len(explanation.overview) > 0
    assert len(explanation.triage_prioritization_rationale) > 0
    assert len(explanation.case_rationales) == len(plan.items)


def test_medops_audit_cryptographic_chain(service: MedOpsService):
    plan = service.optimize_schedule()
    plan_hash = compute_hospital_plan_hash(plan)
    assert len(plan_hash) == 64

    # Sign off as Chief of Surgery
    rec = service.approve_schedule(
        plan_id=plan.plan_id,
        approved_by="Dr. Victor Vance, MD, Chief of Surgical Services",
        notes="OR Master Plan approved for execution",
    )
    assert rec.event_type == "OR_PLAN_APPROVED"
    assert plan.approved is True

    is_valid, msg = service.audit.verify_chain_integrity()
    assert is_valid is True
    assert "verified" in msg.lower()


def test_medops_audit_prevents_invalid_approval(service: MedOpsService):
    plan = service.optimize_schedule()
    plan.summary.validation_passed = False
    plan.summary.validation_violations = ["Simulated sterility breach"]

    with pytest.raises(ValueError, match="Cannot approve invalid surgical schedule"):
        service.approve_schedule(plan.plan_id, approved_by="Chief")


# =========================================================================
# 7. REST API Endpoints Tests
# =========================================================================

def test_api_universal_solve(client: TestClient):
    payload = {
        "problem": {
            "problem_id": "TEST-UNIV-API",
            "domain": "industrial_maintenance",
            "resources": [
                {"id": "BAY-1", "name": "Maintenance Bay 1", "kind": "space", "capabilities": ["heavy_repair"]},
            ],
            "tasks": [
                {"id": "JOB-1", "name": "Turbine Overhaul", "duration_minutes": 180, "priority": 1, "required_capabilities": ["heavy_repair"]},
            ],
        }
    }
    resp = client.post("/api/v1/universal/solve", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["solver_status"] in ("optimal", "feasible")
    assert data["scheduled_tasks"] == 1


def test_api_medops_overview_and_rooms(client: TestClient):
    resp = client.get("/api/v1/medops/overview")
    assert resp.status_code == 200
    ov = resp.json()
    assert ov["operating_rooms_count"] == 5
    assert ov["medical_staff_count"] == 12

    rooms_resp = client.get("/api/v1/medops/rooms")
    assert rooms_resp.status_code == 200
    assert len(rooms_resp.json()) == 5


def test_api_medops_optimize_and_retrieve(client: TestClient):
    opt_resp = client.post("/api/v1/medops/optimize")
    assert opt_resp.status_code == 200
    plan = opt_resp.json()
    assert plan["summary"]["solver_status"] in ("optimal", "feasible")
    assert len(plan["items"]) > 0

    p_id = plan["plan_id"]
    get_resp = client.get(f"/api/v1/medops/plan/{p_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["plan_id"] == p_id


def test_api_medops_simulate(client: TestClient):
    client.post("/api/v1/medops/optimize")
    sim_payload = {
        "delta": {
            "decontaminated_or_rooms": ["OR-GENERAL-SUITE"],
        }
    }
    resp = client.post("/api/v1/medops/simulate", json=sim_payload)
    assert resp.status_code == 200
    data = resp.json()
    assert "simulation_plan" in data
    assert "comparison" in data
