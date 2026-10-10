"""Unit tests for GeCompose Incident Investigation domain models."""

from __future__ import annotations

import json
import pytest

from gecompose.investigation_models import (
    DiagnosticTest,
    Evidence,
    EvidenceLink,
    EvidenceRelationshipType,
    EvidenceSourceType,
    Hypothesis,
    HypothesisStatus,
    Incident,
    IncidentSeverity,
    IncidentStatus,
    InvestigationReport,
)


def test_evidence_creation_and_validation():
    ev = Evidence(
        id="ev_001",
        source_type=EvidenceSourceType.LOGS,
        summary="HTTP 504 Gateway Timeout burst on endpoint /api/v1/auth",
        timestamp="2026-10-10T14:00:00Z",
        source_ref="var/log/nginx/access.log:4521",
        details={"status_code": 504, "count": 142},
        reliability=0.95,
    )
    assert ev.id == "ev_001"
    assert ev.source_type == EvidenceSourceType.LOGS
    assert ev.details["status_code"] == 504
    assert ev.reliability == 0.95

    # Rejection of empty summary or ID
    with pytest.raises(ValueError):
        Evidence(id="  ", source_type=EvidenceSourceType.LOGS, summary="Valid")

    with pytest.raises(ValueError):
        Evidence(id="ev_1", source_type=EvidenceSourceType.LOGS, summary="   ")


def test_incident_creation_and_defaults():
    inc = Incident(
        id="inc_42",
        title="Authentication API Degradation",
        affected_component="auth-service",
        severity=IncidentSeverity.CRITICAL,
    )
    assert inc.id == "inc_42"
    assert inc.status == IncidentStatus.OPEN
    assert inc.severity == IncidentSeverity.CRITICAL
    assert inc.environment == "production"

    with pytest.raises(ValueError):
        Incident(id="", title="Title", affected_component="auth")


def test_evidence_link_and_hypothesis_properties():
    link_sup = EvidenceLink(
        evidence_id="ev_001",
        relationship=EvidenceRelationshipType.SUPPORTS,
        explanation="High latency correlates with upstream timeout",
    )
    link_con = EvidenceLink(
        evidence_id="ev_002",
        relationship=EvidenceRelationshipType.CONTRADICTS,
        explanation="CPU usage remained below 15%",
    )
    link_inc = EvidenceLink(
        evidence_id="ev_003",
        relationship=EvidenceRelationshipType.INCONCLUSIVE,
        explanation="Network switch metric was missing during window",
    )

    hyp = Hypothesis(
        id="hyp_cpu_spike",
        title="CPU Starvation on Auth Nodes",
        description="Nodes became CPU bound due to cryptographic hash flood",
        evidence_links=[link_sup, link_con, link_inc],
        assumptions=["Autoscaling was disabled"],
        unresolved_questions=["Were worker threads pinned?"],
    )

    assert hyp.supporting_evidence_ids == ["ev_001"]
    assert hyp.contradicting_evidence_ids == ["ev_002"]
    assert hyp.inconclusive_evidence_ids == ["ev_003"]
    assert hyp.is_refuted is True


def test_diagnostic_test_model():
    diag = DiagnosticTest(
        id="diag_001",
        name="Inspect Connection Pool Metrics",
        purpose="Determine if DB connection exhaustion caused gateway timeouts",
        target_component="postgresql-primary",
        procedure="SELECT count(*) FROM pg_stat_activity WHERE state = 'active';",
        expected_observations={
            "hyp_db_pool_exhaustion": "Active connection count equals max_connections (200)",
            "hyp_upstream_dns": "Active connection count is low (<10)",
        },
        discriminates_hypotheses=["hyp_db_pool_exhaustion", "hyp_upstream_dns"],
    )
    assert diag.id == "diag_001"
    assert "hyp_db_pool_exhaustion" in diag.expected_observations
    assert len(diag.discriminates_hypotheses) == 2


def test_investigation_report_model_and_json_serialization():
    inc = Incident(
        id="inc_101",
        title="Payment Gateway Outage",
        affected_component="payment-service",
    )
    ev = Evidence(
        id="ev_log_1",
        source_type=EvidenceSourceType.ALERTS,
        summary="PagerDuty P1: Error rate > 50%",
    )
    hyp = Hypothesis(
        id="hyp_third_party_down",
        title="Upstream PSP Downtime",
        evidence_links=[
            EvidenceLink(evidence_id="ev_log_1", relationship=EvidenceRelationshipType.SUPPORTS)
        ],
    )
    test = DiagnosticTest(
        id="test_curl",
        name="Curl PSP Health Endpoint",
        purpose="Verify PSP network reachability",
        target_component="payment-gateway",
        procedure="curl -Iv https://psp.example.com/healthz",
    )

    report = InvestigationReport(
        incident=inc,
        hypotheses=[hyp],
        evidence_trail=[ev],
        missing_evidence=["Outbound network gateway egress flow logs"],
        proposed_tests=[test],
        leading_hypothesis_id="hyp_third_party_down",
        confidence_assessment="Plausible but unconfirmed pending network probe",
    )

    assert report.has_unrefuted_hypothesis is True
    assert report.total_evidence_count == 1
    assert report.total_hypotheses_count == 1

    dumped = report.model_dump(mode="json")
    assert isinstance(dumped, dict)
    assert dumped["incident"]["id"] == "inc_101"
    assert dumped["hypotheses"][0]["supporting_evidence_ids"] == ["ev_log_1"]
    assert json.dumps(dumped)  # JSON-serializable
