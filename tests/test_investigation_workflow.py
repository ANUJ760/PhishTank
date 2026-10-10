"""End-to-end integration and workflow tests for the AI Incident Investigation Engine."""

from __future__ import annotations

import json
import pytest

from gecompose.api import (
    GeComposeEngine,
    investigate_incident,
    serialize_result,
)
from gecompose.exceptions import ValidationError
from gecompose.investigation_models import (
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


def test_e2e_investigation_with_explicit_competing_hypotheses():
    """Simulate a real-world payment service outage with 3 competing hypotheses."""
    incident = Incident(
        id="INC-8912",
        title="Payment Service Spike in HTTP 504 Gateway Timeouts",
        description="Checkout traffic failing at payment processing step",
        affected_component="payment-service",
        severity=IncidentSeverity.CRITICAL,
        start_time="2026-10-10T14:15:00Z",
    )

    evidence = [
        Evidence(
            id="ev_alert_504",
            source_type=EvidenceSourceType.ALERTS,
            summary="PagerDuty P1: payment-service 504 error rate exceeded 25%",
            timestamp="2026-10-10T14:16:00Z",
            source_ref="pagerduty.com/alerts/PD-99",
            reliability=1.0,
        ),
        Evidence(
            id="ev_psp_status",
            source_type=EvidenceSourceType.DOCUMENTS,
            summary="Stripe Status page reports operational degraded performance in US-East",
            timestamp="2026-10-10T14:18:00Z",
            source_ref="status.stripe.com/incidents/abc",
            reliability=0.9,
        ),
        Evidence(
            id="ev_log_timeout",
            source_type=EvidenceSourceType.LOGS,
            summary="Client timeout connecting to https://api.stripe.com/v1/charges after 5000ms",
            timestamp="2026-10-10T14:17:30Z",
            source_ref="var/log/payment/app.log",
            details={"endpoint": "/v1/charges", "timeout_ms": 5000},
            reliability=0.95,
        ),
        Evidence(
            id="ev_cpu_metric",
            source_type=EvidenceSourceType.METRICS,
            summary="payment-service container CPU utilization steady at 18%",
            timestamp="2026-10-10T14:20:00Z",
            source_ref="datadog.com/metrics/payment.cpu",
            reliability=1.0,
        ),
        Evidence(
            id="ev_deploy_ticket",
            source_type=EvidenceSourceType.TICKETS,
            summary="Jira REL-442: Zero payment-service deployments in the past 7 days",
            source_ref="jira.corp/REL-442",
            reliability=0.95,
        ),
    ]

    # Competing Hypotheses:
    # 1. Upstream PSP Outage (supported by PSP status + client timeout log + alerts)
    h_upstream = Hypothesis(
        id="hyp_psp_outage",
        title="Upstream PSP Degradation",
        description="Third-party payment processor is timing out on charge authorization requests",
        root_cause_category="dependency_failure",
        evidence_links=[
            EvidenceLink(evidence_id="ev_alert_504", relationship=EvidenceRelationshipType.SUPPORTS),
            EvidenceLink(evidence_id="ev_psp_status", relationship=EvidenceRelationshipType.SUPPORTS),
            EvidenceLink(evidence_id="ev_log_timeout", relationship=EvidenceRelationshipType.SUPPORTS),
        ],
        assumptions=["Outage is isolated to US-East PSP gateway"],
        unresolved_questions=["Are other payment gateways (e.g. PayPal fallback) functional?"],
    )

    # 2. Local Container CPU Overload (refuted by CPU metric)
    h_cpu = Hypothesis(
        id="hyp_cpu_exhaustion",
        title="Container CPU Saturation",
        description="Application threads starved of CPU cycles causing processing latency",
        root_cause_category="capacity_exhaustion",
        evidence_links=[
            EvidenceLink(evidence_id="ev_alert_504", relationship=EvidenceRelationshipType.SUPPORTS),
            EvidenceLink(
                evidence_id="ev_cpu_metric",
                relationship=EvidenceRelationshipType.CONTRADICTS,
                explanation="Container CPU is normal at 18%",
            ),
        ],
    )

    # 3. Bad Code Release Regression (refuted by deployment ticket)
    h_deploy = Hypothesis(
        id="hyp_bad_deploy",
        title="Recent Release Regression",
        description="Newly released code introduced thread deadlock or infinite loop",
        root_cause_category="configuration_error",
        evidence_links=[
            EvidenceLink(
                evidence_id="ev_deploy_ticket",
                relationship=EvidenceRelationshipType.CONTRADICTS,
                explanation="No deployment occurred in the last 7 days",
            ),
        ],
    )

    engine = GeComposeEngine()
    report = engine.investigate_incident(
        incident, evidence, hypotheses=[h_cpu, h_deploy, h_upstream]
    )

    assert isinstance(report, InvestigationReport)
    assert report.incident.id == "INC-8912"
    assert report.total_evidence_count == 5
    assert report.total_hypotheses_count == 3

    # H_upstream should be leading and STRONGLY_SUPPORTED
    assert report.leading_hypothesis_id == "hyp_psp_outage"
    lead = next(h for h in report.hypotheses if h.id == "hyp_psp_outage")
    assert lead.status == HypothesisStatus.STRONGLY_SUPPORTED
    assert lead.plausibility_score >= 0.75
    assert lead.is_refuted is False

    # H_cpu and H_deploy must be REFUTED
    cpu_hyp = next(h for h in report.hypotheses if h.id == "hyp_cpu_exhaustion")
    assert cpu_hyp.status == HypothesisStatus.REFUTED
    assert cpu_hyp.is_refuted is True
    assert cpu_hyp.plausibility_score == 0.0

    deploy_hyp = next(h for h in report.hypotheses if h.id == "hyp_bad_deploy")
    assert deploy_hyp.status == HypothesisStatus.REFUTED
    assert deploy_hyp.is_refuted is True

    # Missing evidence tracked
    assert len(report.missing_evidence) >= 1
    assert any("US-East PSP gateway" in gap for gap in report.missing_evidence)

    # Proposed diagnostic test
    assert len(report.proposed_tests) >= 1
    confirm_test = report.proposed_tests[0]
    assert "hyp_psp_outage" in confirm_test.discriminates_hypotheses

    # Serialization test
    dumped = engine.serialize_result(report)
    assert isinstance(dumped, dict)
    assert dumped["leading_hypothesis_id"] == "hyp_psp_outage"
    assert json.dumps(dumped)


def test_investigation_with_automated_hypothesis_synthesis():
    """When no explicit hypotheses are provided, engine synthesizes baseline archetypes."""
    incident = Incident(
        id="INC-5511",
        title="Cache Cluster High Eviction Latency",
        affected_component="redis-cluster",
    )
    evidence = [
        Evidence(
            id="ev_mem",
            source_type=EvidenceSourceType.METRICS,
            summary="Memory usage at 99.8% capacity with high evictions",
        ),
        Evidence(
            id="ev_timeout",
            source_type=EvidenceSourceType.LOGS,
            summary="Client timeout acquiring cache lock",
        ),
    ]

    report = investigate_incident(incident, evidence)
    assert len(report.hypotheses) >= 2
    # Resource exhaustion archetype should match memory pressure
    res_hyp = next(h for h in report.hypotheses if h.id == "hyp_resource_exhaustion")
    assert "ev_mem" in res_hyp.supporting_evidence_ids


def test_investigation_from_dict_inputs():
    """Verify that plain dict inputs are properly coerced and validated at API boundary."""
    raw_incident = {
        "id": "INC-77",
        "title": "Ingestion Pipeline Lag",
        "affected_component": "kafka-ingest",
        "severity": "high",
    }
    raw_evidence = [
        {
            "id": "ev_lag",
            "source_type": "alerts",
            "summary": "Consumer lag exceeds 1,000,000 offsets",
            "reliability": 1.0,
        }
    ]

    report = investigate_incident(raw_incident, raw_evidence)
    assert report.incident.id == "INC-77"
    assert len(report.evidence_trail) == 1
    assert report.evidence_trail[0].id == "ev_lag"


def test_investigation_with_empty_evidence():
    """Verify engine handles empty evidence gracefully without crashing."""
    incident = Incident(
        id="INC-EMPTY",
        title="Mystery Alert with zero telemetry",
        affected_component="gateway",
    )
    report = investigate_incident(incident, [])
    assert len(report.evidence_trail) == 0
    assert len(report.missing_evidence) >= 1
    assert report.leading_hypothesis_id is None
    assert "No quantitative timeseries metrics" in report.missing_evidence[0]


def test_investigation_rejects_malformed_input():
    """Verify structured ValidationError on bad dictionary inputs."""
    bad_incident = {
        "id": "",  # invalid empty ID
        "title": "Bad",
        "affected_component": "foo",
    }
    with pytest.raises(ValidationError):
        investigate_incident(bad_incident, [])

    with pytest.raises(TypeError):
        investigate_incident("not a dict or incident", [])  # type: ignore


def test_investigation_contradiction_overrides_support():
    """Critical epistemological property: a fatal contradiction refutes even highly supported hypotheses."""
    incident = Incident(
        id="INC-CONTRADICT",
        title="Service Failure",
        affected_component="billing",
    )
    evidence = [
        Evidence(id="ev_alert", source_type=EvidenceSourceType.ALERTS, summary="Alert fired"),
        Evidence(id="ev_log", source_type=EvidenceSourceType.LOGS, summary="Log symptom"),
        Evidence(id="ev_proof", source_type=EvidenceSourceType.METRICS, summary="Fatal counterproof"),
    ]

    hyp = Hypothesis(
        id="hyp_tested",
        title="Proposed Cause",
        evidence_links=[
            EvidenceLink(evidence_id="ev_alert", relationship=EvidenceRelationshipType.SUPPORTS),
            EvidenceLink(evidence_id="ev_log", relationship=EvidenceRelationshipType.SUPPORTS),
            EvidenceLink(
                evidence_id="ev_proof",
                relationship=EvidenceRelationshipType.CONTRADICTS,
                explanation="Smoking gun proves cause was impossible",
            ),
        ],
    )

    report = investigate_incident(incident, evidence, hypotheses=[hyp])
    evaluated = report.hypotheses[0]
    assert evaluated.status == HypothesisStatus.REFUTED
    assert evaluated.plausibility_score == 0.0
    assert evaluated.is_refuted is True
