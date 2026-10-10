"""Comprehensive tests for Starlette REST API endpoints in backend/server.py."""
from __future__ import annotations

import json
import pytest
from starlette.testclient import TestClient

from backend import config
from backend.server import app


@pytest.fixture(scope="module")
def client():
    return TestClient(app)


def test_index_html(client):
    res = client.get("/")
    assert res.status_code == 200
    assert "GeCompose Backend" in res.text


def test_health_endpoint(client):
    res = client.get("/health")
    assert res.status_code == 200
    data = res.json()
    assert "items" in data
    assert "database" in data["items"]
    assert data["items"]["database"]["ok"] is True


def test_demo_seed_and_lifecycle(client):
    # 1. Reset demo
    res_reset = client.post("/demo/reset")
    assert res_reset.status_code == 200

    # 2. Seed demo
    res_seed = client.post("/demo/seed")
    assert res_seed.status_code == 200
    assert res_seed.json()["status"] == "seeded"

    # 3. Check roster
    res_roster = client.get("/roster")
    assert res_roster.status_code == 200
    roster_data = res_roster.json()
    assert len(roster_data["teachers"]) > 0

    # 4. Check rules
    res_rules = client.get("/rules")
    assert res_rules.status_code == 200
    rules = res_rules.json()["rules"]
    assert len(rules) >= 2

    # 5. Check confirmed rules
    res_confirmed = client.get("/rules?status=confirmed")
    assert res_confirmed.status_code == 200
    assert len(res_confirmed.json()["rules"]) >= 2

    # 6. Check schedule
    res_sched = client.get("/schedule")
    assert res_sched.status_code == 200
    sched = res_sched.json()
    assert sched["version"] >= 1
    assert len(sched["placements"]) > 0

    # 7. Check why cell
    res_why = client.get("/why/DB_LAB")
    assert res_why.status_code == 200
    why_data = res_why.json()
    assert why_data["session_id"] == "DB_LAB"

    # 8. Check audit events
    res_events = client.get("/events")
    assert res_events.status_code == 200
    events = res_events.json()["events"]
    assert len(events) >= 3

    # 9. Test export formats
    res_json = client.get("/export/json")
    assert res_json.status_code == 200
    assert res_json.headers["content-type"] == "application/json"

    res_csv = client.get("/export/csv")
    assert res_csv.status_code == 200
    assert "text/csv" in res_csv.headers["content-type"]

    res_ics = client.get("/export/ics")
    assert res_ics.status_code == 200
    assert "text/calendar" in res_ics.headers["content-type"]

    # 10. Test verification
    res_verify = client.post("/verify", content=res_json.content)
    assert res_verify.status_code == 200
    assert res_verify.json()["match"] is True
    assert res_verify.json()["anchored"] is True


def test_rule_crud(client):
    new_rule = {
        "id": "R_CUSTOM_TEST",
        "type": "teacher_unavailable",
        "owner": "Prof. Rao",
        "params": {"teacher": "Prof. Rao", "day": 1, "slots": [0]},
        "status": "draft",
    }
    res_create = client.post("/rules", json=new_rule)
    assert res_create.status_code == 201

    # Edit rule
    res_edit = client.post(
        "/rules/R_CUSTOM_TEST",
        json={"params": {"teacher": "Prof. Rao", "day": 1, "slots": [0, 1]}},
    )
    assert res_edit.status_code == 200
    assert res_edit.json()["params"]["slots"] == [0, 1]

    # Confirm rule
    res_confirm = client.post("/rules/R_CUSTOM_TEST/confirm")
    assert res_confirm.status_code == 200
    assert res_confirm.json()["status"] == "confirmed"


def test_solve_endpoint(client):
    res_solve = client.post("/solve?minimal_change=true")
    assert res_solve.status_code == 200
    data = res_solve.json()
    assert data["status"] in {"feasible", "infeasible"}


def test_scoreboard_endpoint(client, monkeypatch):
    monkeypatch.setattr(config, "MOCK_LLM", True)
    res = client.get("/scoreboard?runs=2")
    assert res.status_code == 200
    assert len(res.json()["rows"]) == 2
