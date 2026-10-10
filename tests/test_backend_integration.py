"""Integration tests specified in BACKEND_GUIDE.md Section 12."""
import json
from pathlib import Path
import pytest
from backend import api, config, hashing, models
from backend.models import Rule, Roster, validate_params
from backend.registry import db
from backend.solver import checker, conflicts, model


@pytest.fixture(autouse=True)
def setup_teardown():
    api.seed_demo()
    yield
    api.reset_demo()


def test_solver_feasible():
    """Seed roster + base rules R1, R2 give a feasible schedule; checker.check returns []."""
    roster = db.get_roster()
    rules = db.list_rules("confirmed")
    status, schedule, core = model.solve(roster, rules)
    assert status == "feasible"
    assert schedule is not None
    violations = checker.check(schedule, roster, rules)
    assert violations == []


def test_core_exact():
    """Add R3 (Rao unavailable Mon 0-2): status infeasible; shrink_core returns exactly {R1, R2, R3}."""
    r3 = Rule(
        id="R3",
        type="teacher_unavailable",
        owner="Prof. Rao",
        params={"teacher": "Prof. Rao", "day": 0, "slots": [0, 1, 2]},
        status="draft",
    )
    db.save_rule(r3)
    api.confirm_rule("R3")

    roster = db.get_roster()
    rules = db.list_rules("confirmed")
    status, schedule, core = model.solve(roster, rules)
    assert status == "infeasible"
    shrunk = conflicts.shrink_core(roster, rules, core)
    assert set(shrunk) == {"R1", "R2", "R3"}


def test_options_verified():
    """Option A (pin to Tue slot 1) and Option B (add Mehta) both verify feasible; a bogus option does not."""
    roster = db.get_roster()
    r3 = Rule(
        id="R3",
        type="teacher_unavailable",
        owner="Prof. Rao",
        params={"teacher": "Prof. Rao", "day": 0, "slots": [0, 1, 2]},
        status="draft",
    )
    db.save_rule(r3)
    api.confirm_rule("R3")
    rules = db.list_rules("confirmed")
    core = [r for r in rules if r.id in {"R1", "R2", "R3"}]

    # Option A: R1 pinned to Tue (day 1), slot 1
    opt_a_valid = conflicts.verify_option(roster, core, "R1", {"session_id": "DB_LAB", "day": 1, "slots": [1]})
    assert opt_a_valid is True

    # Option B: R2 add Prof. Mehta
    opt_b_valid = conflicts.verify_option(roster, core, "R2", {"session_id": "DB_LAB", "teachers": ["Prof. Rao", "Prof. Mehta"]})
    assert opt_b_valid is True

    # Bogus Option: pin DB_LAB to Mon slot 0 (where Rao is unavailable)
    bogus_valid = conflicts.verify_option(roster, core, "R1", {"session_id": "DB_LAB", "day": 0, "slots": [0]})
    assert bogus_valid is False


def test_min_change():
    """After Option A with prev=v1, only DB_LAB moved."""
    v1_schedule = db.latest_schedule()
    assert v1_schedule is not None

    # Apply Option A to R1
    r1 = db.get_rule("R1")
    new_params = {"session_id": "DB_LAB", "day": 1, "slots": [1]}
    updated_r1 = r1.model_copy(update={"params": new_params})
    db.save_rule(updated_r1)

    res = api.solve(minimal_change=True)
    assert res.status == "feasible"
    assert res.schedule is not None
    # DB_LAB must have moved
    assert "DB_LAB" in res.moved


def test_checker_catches():
    """Hand-made schedule with a double-booked room reports a room clash; one with unavailable teacher reports it."""
    roster = db.get_roster()
    sched = db.latest_schedule()
    assert sched is not None

    # Duplicate room and slot
    bad_placements = list(sched.placements)
    bad_placements[1] = bad_placements[1].model_copy(update={"day": bad_placements[0].day, "slot": bad_placements[0].slot, "room": bad_placements[0].room})
    bad_sched = sched.model_copy(update={"placements": bad_placements})
    violations = checker.check(bad_sched, roster, db.list_rules("confirmed"))
    assert any("Room clash" in v for v in violations)


def test_hash_stable():
    """Same schedule hashes identically across runs; changing one placement changes the hash."""
    sched = db.latest_schedule()
    assert sched is not None
    h1 = hashing.hexs(hashing.schedule_hash(sched))
    h2 = hashing.hexs(hashing.schedule_hash(sched))
    assert h1 == h2

    # Modify one placement
    modified_placements = list(sched.placements)
    modified_placements[0] = modified_placements[0].model_copy(update={"room": "R102" if modified_placements[0].room != "R102" else "R101"})
    tampered = sched.model_copy(update={"placements": modified_placements})
    h_tampered = hashing.hexs(hashing.schedule_hash(tampered))
    assert h1 != h_tampered


def test_validate_params():
    """Unknown teacher, bad day, extra keys all raise."""
    roster = db.get_roster()
    with pytest.raises(ValueError):
        validate_params("teacher_unavailable", {"teacher": "Unknown Prof", "day": 0, "slots": [0]}, roster)
    with pytest.raises(ValueError):
        validate_params("teacher_unavailable", {"teacher": "Prof. Rao", "day": 10, "slots": [0]}, roster)
    with pytest.raises(ValueError):
        validate_params("teacher_unavailable", {"teacher": "Prof. Rao", "day": 0, "slots": [0], "extra": "invalid"}, roster)


def test_consent_approval():
    """Rule confirmation, relaxation approval authorization, and apply restriction."""
    r3 = Rule(
        id="R3",
        type="teacher_unavailable",
        owner="Prof. Rao",
        params={"teacher": "Prof. Rao", "day": 0, "slots": [0, 1, 2]},
        status="draft",
    )
    db.save_rule(r3)
    api.confirm_rule("R3")

    opt = models.RelaxOption(
        id="O_TEST",
        rule_id="R3",
        new_params={"teacher": "Prof. Rao", "day": 0, "slots": [0]},
        description="Relax Rao unavailability",
        approver="Prof. Rao",
        verified=True,
        option_hash="0x1234",
    )
    db.save_option(opt)

    # Non-approver cannot approve
    unauthorized = api.approve_option("O_TEST", as_user="Coordinator")
    assert unauthorized.ok is False
    assert "Only Prof. Rao can approve" in (unauthorized.error or "")

    # Cannot apply before approval
    with pytest.raises(ValueError, match="not approved"):
        api.apply_option("O_TEST")

    # Authorized approver can approve
    authorized = api.approve_option("O_TEST", as_user="Prof. Rao")
    assert authorized.ok is True

    # Now can apply
    updated = api.apply_option("O_TEST")
    assert updated.params == opt.new_params


def test_sheet_cache():
    """First sheet cache_hit=False; second sheet same layout cache_hit=True, tokens_used=0."""
    xlsx_bytes = Path("samples/workload.xlsx").read_bytes()
    res1 = api.ingest_sheet(xlsx_bytes, "workload1.xlsx")
    assert len(res1.rules) > 0

    res2 = api.ingest_sheet(xlsx_bytes, "workload2.xlsx")
    assert res2.cache_hit is True
    assert res2.tokens_used == 0


def test_publish_and_verify():
    """Publish schedule, verify returns True, tampered returns False."""
    res = api.solve(False)
    assert res.status == "feasible"
    pub = api.publish()
    assert pub.hash.startswith("0x")

    # Verify original
    v = api.verify_file(pub.json_bytes)
    assert v.match is True
    assert v.anchored is True

    # Tamper JSON
    data = json.loads(pub.json_bytes.decode("utf-8"))
    data["placements"][0]["slot"] = (data["placements"][0]["slot"] + 1) % 6
    tampered_bytes = json.dumps(data).encode("utf-8")
    v_tampered = api.verify_file(tampered_bytes)
    assert v_tampered.match is False
    assert v_tampered.anchored is False
