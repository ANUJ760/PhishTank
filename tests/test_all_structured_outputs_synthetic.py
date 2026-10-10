"""Comprehensive end-to-end verification of all structured outputs across all domains using synthetic test data.

Verifies:
1. Intake & Data Dump Output (Grounded Roster, Draft Rules, Human Rule Cards).
2. Solver Output (CP-SAT Schedule, Placements, Hard Constraint Satisfaction).
3. Publication Output (PublishResult, RFC 5545 ICS, CSV, Canonical JSON, SHA-256 Digest).
4. Independent Checker Output (Valid schedule passes, corrupted schedule flagged).
5. Conflict & Explainability Output (MUS Extraction, Plain-English ExplainOut, RelaxOptions).
6. Campus Disruption Recovery Output (ImpactReport, Minimal-Perturbation Recovery).
7. MedOps Structured Output (HospitalORPlan, Triage Preemption, Surgical Turnaround).
8. ReliefOps Structured Output (AllocationPlan, Multi-Camp Inventory, Bottleneck Explanation).
9. Universal Constraint Solver Output (Precedence DAG, Multi-Resource Assignments).
10. AI Incident Investigation Output (InvestigationReport, Plausibility Scoring, Diagnostic Probes).
11. Frontend API Endpoint Serving (All HTTP endpoints return valid structured schemas with 0 raw JSON dumps).
"""
from __future__ import annotations

import json
import pytest
from starlette.testclient import TestClient

from backend.http.app import app
from backend.http.auth import seed_demo_users
from backend import api
from backend.models import (
    Roster,
    Room,
    Session,
    Rule,
    Schedule,
    Placement,
    DraftRulesOut,
    DraftRule,
)
from backend.intake.data_dump import ingest_data_dump
from backend.solver.checker import check
from backend.hashing import schedule_hash, hexs

# Specialized domain imports
from gecompose import (
    GeComposeEngine,
    DisruptionEvent,
    ResourceType,
    Incident,
    Evidence,
    Hypothesis,
    investigate_incident,
    IncidentSeverity,
    EvidenceSourceType,
    EvidenceRelationshipType,
    TimeSlot as GCTimeSlot,
    Teacher as GCTeacher,
    Room as GCRoom,
    Session as GCSession,
    SchedulingProblem as GCSchedulingProblem,
)
from gecompose.diagnostics import diagnose_conflicts
from backend.medops import (
    MedOpsService,
    PatientCase,
    OperatingRoom,
    MedicalStaff,
    SurgicalSpecialty,
    StaffRole,
    TriageUrgency,
    WhatIfHospitalDelta,
    compute_hospital_plan_hash,
)
from backend.reliefops import (
    ReliefOpsService,
    ReliefCamp,
    Warehouse,
    InventoryItem,
    Vehicle,
    ReliefRequest,
    ResourceType as ROResourceType,
    ResourceCategory as ROResourceCategory,
    UrgencyLevel as ROUrgencyLevel,
    WhatIfDelta as ROWhatIfDelta,
    compute_plan_hash,
)
from backend.universal import (
    UniversalConstraintSolver,
    UniversalProblem,
    UniversalTask,
    UniversalResource,
    ResourceKind,
    ConstraintPriority,
)


@pytest.fixture(autouse=True)
def clean_environment():
    """Reset database and memory state between test executions."""
    api.reset_demo(keep_parsers=True)
    api.seed_demo()
    seed_demo_users()
    yield


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


# =========================================================================
# 1. Intake & Data Dump Structured Output Verification
# =========================================================================
def test_synthetic_data_dump_structured_output():
    """Synthetic prompt dump containing real professors, rooms, and constraints."""
    files = [
        ("roster_sample.csv", b"Faculty,Course,Room,Capacity\nProf. Alice Vance,CS501,Room 101,60\nProf. Bob Chen,CS502,Lab 202,30\nProf. Catherine Miller,CS503,Room 101,60\n"),
        ("memo.txt", b"Prof. Alice Vance cannot take classes on Monday morning between 09:00 and 12:00.\nLab 202 is unavailable on Tuesday due to hardware maintenance.\n"),
    ]
    instructions = "Extract professor availability and lab constraints."
    notes = "CS501 is pinned to Wednesday slot 2. CS502 is only qualified for Prof. Bob Chen."

    result = ingest_data_dump(files=files, instructions=instructions, notes=notes)

    # 1. Summary & files check
    assert result.summary != ""
    assert len(result.processed_files) == 2
    assert result.instructions_executed == instructions

    # 2. Rule structure check
    assert len(result.rules) >= 2
    rule_types = {r.type for r in result.rules}
    assert "teacher_unavailable" in rule_types or "room_unavailable" in rule_types

    # 3. Rule cards structure check (for human-facing UI, 0 raw JSON)
    assert len(result.rule_cards) == len(result.rules)
    for card in result.rule_cards:
        assert card.headline != ""
        assert card.category != ""
        assert card.plain_description != ""
        assert card.target_entity != ""
        assert card.time_window != ""
        assert not card.plain_description.startswith("{")  # Ensure not raw JSON


# =========================================================================
# 2. CP-SAT Solver Structured Output Verification
# =========================================================================
def test_synthetic_solver_structured_output():
    """Verify mathematical solver produces valid Schedule and Placements."""
    roster = Roster(
        teachers=["Dr. Ada Lovelace", "Dr. Claude Shannon"],
        rooms=[
            Room(name="Auditorium A", capacity=100),
            Room(name="Seminar B", capacity=40),
        ],
        sessions=[
            Session(id="INFO_THEORY", course="Information Theory", teachers=["Dr. Claude Shannon"], size=35),
            Session(id="COMP_PROG", course="Computer Programming", teachers=["Dr. Ada Lovelace"], size=80),
        ],
    )
    api.db.save_roster(roster)

    # Add confirmed rules
    rule1 = Rule(
        id="R_ADA_PIN",
        type="pin_session",
        owner="Dean",
        params={"session_id": "COMP_PROG", "day": 1, "slots": [1]},
        status="confirmed",
    )
    api.db.save_rule(rule1)

    solve_res = api.solve(minimal_change=False)
    assert solve_res.status == "feasible"
    assert solve_res.schedule is not None
    assert solve_res.solve_ms >= 0
    assert len(solve_res.schedule.placements) == 2

    # Verify each placement adheres strictly to the Placement schema
    for p in solve_res.schedule.placements:
        assert isinstance(p.session_id, str)
        assert isinstance(p.teacher, str)
        assert isinstance(p.room, str)
        assert 0 <= p.day < 5
        assert 0 <= p.slot < 6

    # Verify mathematical invariants
    teacher_slots = set()
    room_slots = set()
    for p in solve_res.schedule.placements:
        assert (p.teacher, p.day, p.slot) not in teacher_slots, "Teacher double-booking detected!"
        assert (p.room, p.day, p.slot) not in room_slots, "Room double-booking detected!"
        teacher_slots.add((p.teacher, p.day, p.slot))
        room_slots.add((p.room, p.day, p.slot))

    # Verify explainability: "Why is this cell here?"
    why_ada = api.why_cell("COMP_PROG")
    assert len(why_ada) > 0
    assert any(r.id == "R_ADA_PIN" for r in why_ada)


# =========================================================================
# 3. Publication & Cryptographic Ledger Structured Output Verification
# =========================================================================
def test_synthetic_publication_artifacts_output():
    """Verify publish() generates valid ICS calendar, CSV tabular, and SHA-256 receipts."""
    roster = Roster(
        teachers=["Prof. Gauss"],
        rooms=[Room(name="Math Lab", capacity=50)],
        sessions=[Session(id="MATH101", course="Calculus I", teachers=["Prof. Gauss"], size=40)],
    )
    api.db.save_roster(roster)

    solve_res = api.solve(minimal_change=False)
    assert solve_res.status == "feasible"

    pub_res = api.publish()

    # Check PublishResult structure
    assert pub_res.version >= 1
    assert pub_res.hash.startswith("0x")
    assert pub_res.tx_hash == pub_res.hash
    assert pub_res.json_bytes is not None
    assert pub_res.csv_bytes is not None
    assert pub_res.ics_bytes is not None

    # 1. Check RFC 5545 iCalendar export
    ics_text = pub_res.ics_bytes.decode("utf-8")
    assert "BEGIN:VCALENDAR" in ics_text
    assert "END:VCALENDAR" in ics_text
    assert "BEGIN:VEVENT" in ics_text
    assert "Calculus I" in ics_text
    assert "LOCATION:Math Lab" in ics_text

    # 2. Check Tabular CSV export
    csv_text = pub_res.csv_bytes.decode("utf-8")
    lines = csv_text.strip().splitlines()
    assert "session_id,teacher,room,day,time" in lines[0].lower()
    assert len(lines) == 2  # Header + 1 record
    assert "MATH101" in lines[1]
    assert "Prof. Gauss" in lines[1]

    # 3. Check Canonical SHA-256 Verification
    verify_ok = api.verify_file(pub_res.json_bytes)
    assert verify_ok.match is True
    assert verify_ok.anchored is True
    assert verify_ok.recomputed_hash == pub_res.hash

    # 4. Check Tamper Catch: alter 1 slot in JSON
    parsed = json.loads(pub_res.json_bytes)
    parsed["placements"][0]["slot"] = (parsed["placements"][0]["slot"] + 1) % 6
    tampered_bytes = json.dumps(parsed).encode("utf-8")
    verify_tampered = api.verify_file(tampered_bytes)
    assert verify_tampered.match is False
    assert verify_tampered.anchored is False


# =========================================================================
# 4. Independent Verification Checker Output
# =========================================================================
def test_independent_checker_output():
    """Verify checker validates clean schedules and flags violations on corrupted ones."""
    roster = Roster(
        teachers=["Prof. Euler"],
        rooms=[Room(name="Euler Hall", capacity=30)],
        sessions=[Session(id="NUM_THEORY", course="Number Theory", teachers=["Prof. Euler"], size=25)],
    )
    rule = Rule(
        id="R_EULER_RESTRICT",
        type="teacher_unavailable",
        owner="Admin",
        params={"teacher": "Prof. Euler", "day": 0, "slots": [0]},
        status="confirmed",
    )

    clean_sched = Schedule(
        version=1,
        placements=[Placement(session_id="NUM_THEORY", teacher="Prof. Euler", room="Euler Hall", day=1, slot=2)],
    )
    violations = check(clean_sched, roster, [rule])
    assert len(violations) == 0

    # Corrupt schedule to violate rule
    corrupt_sched = Schedule(
        version=1,
        placements=[Placement(session_id="NUM_THEORY", teacher="Prof. Euler", room="Euler Hall", day=0, slot=0)],
    )
    violations_caught = check(corrupt_sched, roster, [rule])
    assert len(violations_caught) > 0
    assert any("teaches NUM_THEORY while unavailable" in v for v in violations_caught)


# =========================================================================
# 5. Infeasibility & Conflict Diagnostic Structured Output
# =========================================================================
def test_synthetic_conflict_diagnosis_structured_output():
    """Introduce conflicting rules, verify MUS extraction and ExplainOut schema."""
    # Seed conflicting demo scenario with R1, R2, R3
    api.seed_demo()
    # Add third conflicting rule pinning Prof. Rao unavailable when DB_LAB is pinned
    r3 = Rule(
        id="R3",
        type="teacher_unavailable",
        owner="Prof. Rao",
        params={"teacher": "Prof. Rao", "day": 0, "slots": [0, 1, 2]},
        status="confirmed",
    )
    api.db.save_rule(r3)

    solve_res = api.solve(minimal_change=False)
    assert solve_res.status == "infeasible"
    assert solve_res.conflict is not None
    assert len(solve_res.conflict.rule_ids) >= 2

    explanation = api.explain_conflict(solve_res.conflict)
    assert explanation.summary != ""
    assert len(explanation.options) == 2

    for opt in explanation.options:
        assert opt.id != ""
        assert opt.rule_id in {"R1", "R2"}
        assert isinstance(opt.new_params, dict)
        assert opt.description != ""
        assert opt.verified is True

    # Also test domain core diagnosis
    diag_problem = GCSchedulingProblem(
        teachers=[GCTeacher(id="t_rao", name="Prof. Rao", qualifications={"Databases"}, unavailable_slots={"mon_09"})],
        rooms=[GCRoom(id="r1", name="Lab 1", capacity=50)],
        slots=[
            GCTimeSlot(id="mon_09", day="Monday", start_time="09:00", end_time="10:00"),
            GCTimeSlot(id="mon_10", day="Monday", start_time="10:00", end_time="11:00"),
        ],
        sessions=[GCSession(id="sess_db", subject="Databases", pinned_teacher_id="t_rao", pinned_slot_id="mon_09")],
    )
    diag = diagnose_conflicts(diag_problem)
    assert diag.is_infeasible is True
    assert diag.is_minimal is True
    assert diag.has_core is True


# =========================================================================
# 6. Campus Disruption Recovery Structured Output
# =========================================================================
def test_synthetic_campus_disruption_recovery_output():
    """Verify DisruptionRecoveryResult and ImpactReport schemas."""
    engine = GeComposeEngine()

    slots = [
        GCTimeSlot(id="mon_0900", day="Monday", start_time="09:00", end_time="10:00"),
        GCTimeSlot(id="mon_1000", day="Monday", start_time="10:00", end_time="11:00"),
    ]
    teachers = [GCTeacher(id="t_feynman", name="Richard Feynman", qualifications={"Physics"})]
    rooms = [
        GCRoom(id="lab_alpha", name="Alpha Lab", capacity=50),
        GCRoom(id="hall_beta", name="Beta Hall", capacity=80),
    ]
    sessions = [
        GCSession(
            id="quantum_1",
            title="Quantum Mechanics",
            subject="Physics",
            expected_students=40,
            pinned_room_id="lab_alpha",
            pinned_slot_id="mon_0900",
        ),
    ]

    problem = GCSchedulingProblem(slots=slots, teachers=teachers, rooms=rooms, sessions=sessions)
    baseline_res = engine.schedule(problem)
    assert baseline_res.is_success

    # Disruption: Alpha Lab flooded during mon_0900
    disruption = DisruptionEvent(
        id="DISRUPT_FLOOD",
        resource_type=ResourceType.ROOM,
        resource_id="lab_alpha",
        slot_ids={"mon_0900"},
        reason="Facility water leakage",
    )

    impact = engine.analyze_disruption_impact(problem, baseline_res.assignments, disruption)
    assert impact.directly_affected_session_ids == ["quantum_1"]

    recovery = engine.recover_schedule(problem, baseline_res.assignments, disruption)
    assert recovery.is_success is True
    assert recovery.total_changes >= 1
    assert len(recovery.changes) >= 1
    for change in recovery.changes:
        assert change.session_id == "quantum_1"
        assert change.new_assignment.room_id == "hall_beta"


# =========================================================================
# 7. MedOps Hospital Operating Theatre Structured Output
# =========================================================================
def test_synthetic_medops_structured_output():
    """Verify HospitalORPlan, preemption simulation, and SHA-256 audit record."""
    med_service = MedOpsService()
    med_service.registry.seed_level1_trauma_benchmark()

    # 1. Optimize plan
    plan = med_service.optimize_schedule()
    assert plan.summary.solver_status in ("optimal", "feasible")
    assert plan.summary.scheduled_cases > 0
    assert len(plan.items) > 0

    for item in plan.items:
        assert item.case_id != ""
        assert item.or_room_id != ""
        assert item.lead_surgeon_id != ""
        assert item.anesthesiologist_id != ""
        assert item.start_minute >= 0
        assert item.end_minute > item.start_minute

    # 2. Verify SHA-256 plan hash
    plan_hash = compute_hospital_plan_hash(plan)
    assert len(plan_hash) == 64

    # 3. Simulate What-If Delta with Emergent Trauma
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
            )
        ]
    )
    sim_plan, comparison = med_service.run_simulation(delta=delta)
    assert sim_plan.summary.solver_status in ("optimal", "feasible")
    assert comparison.simulation_plan_id != ""


# =========================================================================
# 8. ReliefOps Disaster Supply Allocation Structured Output
# =========================================================================
def test_synthetic_reliefops_structured_output():
    """Verify AllocationPlan, PlanExplanation, and SHA-256 audit record."""
    relief_service = ReliefOpsService()
    relief_service.registry.seed_cyclone_disaster_demo()

    # 1. Optimize aid allocation
    plan = relief_service.optimize_allocation()
    assert plan.summary.solver_status in ("optimal", "feasible")
    assert plan.summary.solve_time_ms >= 0
    assert len(plan.allocations) > 0

    for alloc in plan.allocations:
        assert alloc.camp_id != ""
        assert alloc.allocated_quantity >= 0
        assert 0.0 <= alloc.fulfillment_ratio <= 1.0

    # 2. Plan Hash
    relief_hash = compute_plan_hash(plan)
    assert len(relief_hash) == 64

    # 3. Plan explanation
    explanation = relief_service.explain_plan(plan.plan_id)
    assert explanation.plan_id == plan.plan_id
    assert isinstance(explanation.bottleneck_resources, list)


# =========================================================================
# 9. Universal Domain-Agnostic Optimization Structured Output
# =========================================================================
def test_synthetic_universal_solver_output():
    """Verify UniversalSolution schema with task precedence DAG."""
    problem = UniversalProblem(
        problem_id="UNIV_SYNTHETIC_DAG",
        domain="datacenter_pipeline",
        resources=[
            UniversalResource(id="GPU_NODE_1", name="GPU Cluster Node 1", kind=ResourceKind.EQUIPMENT, capacity=1),
        ],
        tasks=[
            UniversalTask(id="TASK_EXTRACT", name="Data Extraction", priority=ConstraintPriority.HIGH_PRIORITY, duration_minutes=30),
            UniversalTask(
                id="TASK_TRANSFORM",
                name="Feature Transform",
                priority=ConstraintPriority.HIGH_PRIORITY,
                duration_minutes=45,
                precedence_task_ids=["TASK_EXTRACT"],
            ),
        ],
    )

    solver = UniversalConstraintSolver()
    solution = solver.solve(problem)
    assert solution.solver_status in ("optimal", "feasible")
    assert len(solution.assignments) == 2

    extract_assign = next(a for a in solution.assignments if a.task_id == "TASK_EXTRACT")
    transform_assign = next(a for a in solution.assignments if a.task_id == "TASK_TRANSFORM")

    # Strict precedence check
    assert extract_assign.end_minute <= transform_assign.start_minute


# =========================================================================
# 10. AI Incident Investigation Structured Output
# =========================================================================
def test_synthetic_incident_investigation_output():
    """Verify InvestigationReport schema, plausibility scoring, and diagnostic probes."""
    incident = Incident(
        id="INC_TEST_01",
        title="Payment Service DB Saturation",
        severity=IncidentSeverity.HIGH,
        affected_component="payment-db",
    )

    evidence = [
        Evidence(
            id="E1",
            source_type=EvidenceSourceType.LOGS,
            summary="HikariPool: pool exhausted after 30000ms",
            reliability=0.9,
        ),
        Evidence(
            id="E2",
            source_type=EvidenceSourceType.METRICS,
            summary="DB active_connections at 99/100 (99%)",
            reliability=0.95,
        ),
    ]

    hypotheses = [
        Hypothesis(
            id="H_DB_POOL",
            title="Database Connection Pool Exhaustion",
            evidence_links=[
                {"evidence_id": "E1", "relationship": EvidenceRelationshipType.SUPPORTS, "weight": 1.0},
                {"evidence_id": "E2", "relationship": EvidenceRelationshipType.SUPPORTS, "weight": 1.0},
            ],
        ),
    ]

    engine = GeComposeEngine()
    report = engine.investigate_incident(incident=incident, evidence=evidence, hypotheses=hypotheses)
    assert report.leading_hypothesis_id == "H_DB_POOL"
    assert report.confidence_assessment != ""
    assert isinstance(report.missing_evidence, list)
    assert len(report.proposed_tests) >= 1
    assert report.total_evidence_count == 2
    assert report.total_hypotheses_count == 1


# =========================================================================
# 11. Frontend API Endpoint Serving Verification (0 Raw JSON Dumps)
# =========================================================================
def test_frontend_endpoints_serve_valid_structured_data(client: TestClient):
    """Verify all API endpoints consumed by the frontend return valid structured JSON."""
    # Authenticate as coordinator
    login_res = client.post(
        "/api/v1/auth/sign-in",
        json={"email": "admin@gecompose.internal", "password": "password123"},
    )
    assert login_res.status_code == 200
    token = login_res.json()["token"]
    headers = {"Authorization": f"Bearer {token}"}

    api.seed_demo()

    # 1. Roster
    res = client.get("/api/v1/roster", headers=headers)
    assert res.status_code == 200
    roster_data = res.json()
    assert "teachers" in roster_data
    assert "rooms" in roster_data
    assert "sessions" in roster_data

    # 2. Latest Schedule
    res = client.get("/api/v1/schedules/latest", headers=headers)
    assert res.status_code == 200
    sched_data = res.json()
    assert "placements" in sched_data
    assert len(sched_data["placements"]) > 0

    # 3. Why Cell Drilldown
    session_id = sched_data["placements"][0]["session_id"]
    res = client.get(f"/api/v1/schedule/why/{session_id}", headers=headers)
    assert res.status_code == 200
    why_data = res.json()
    assert isinstance(why_data, list)

    # 4. Audit Ledger Entries
    res = client.get("/api/v1/ledger/events", headers=headers)
    assert res.status_code == 200
    ledger_data = res.json()
    assert "events" in ledger_data
    assert len(ledger_data["events"]) > 0

    # 5. Ledger Integrity Check
    res = client.get("/api/v1/ledger/verify", headers=headers)
    assert res.status_code == 200
    assert res.json()["valid"] is True

    # 6. Scoreboard
    res = client.post("/api/v1/scoreboard", json={"runs": 1}, headers=headers)
    assert res.status_code == 200
    sb_data = res.json()
    assert "rows" in sb_data
    assert sb_data["rows"][0]["gecompose_violations"] == 0
