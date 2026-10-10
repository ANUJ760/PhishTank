"""Tests for hypothesis evidence analysis and diagnostic test formulation."""

from __future__ import annotations

import pytest
from gecompose.exceptions import ValidationError
from gecompose.investigation import (
    IncidentInvestigator,
    evaluate_hypothesis,
)
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
)


@pytest.fixture
def sample_incident():
    return Incident(
        id="inc_checkout_failure",
        title="Checkout Service 500 Spike",
        description="Users experiencing checkout failures during flash sale",
        affected_component="checkout-service",
        severity=IncidentSeverity.CRITICAL,
    )


@pytest.fixture
def distributed_evidence():
    return [
        Evidence(
            id="ev_alert",
            source_type=EvidenceSourceType.ALERTS,
            summary="HTTP 500 rate exceeds 15% on checkout-service",
            reliability=1.0,
        ),
        Evidence(
            id="ev_db_log",
            source_type=EvidenceSourceType.LOGS,
            summary="PostgreSQL: FATAL remaining connection slots are reserved for non-replication superuser connections",
            reliability=0.98,
        ),
        Evidence(
            id="ev_metric_cpu",
            source_type=EvidenceSourceType.METRICS,
            summary="Host CPU utilization at 12% across all checkout app pods",
            reliability=0.95,
        ),
        Evidence(
            id="ev_git_deploy",
            source_type=EvidenceSourceType.DOCUMENTS,
            summary="No deployments executed in the last 48 hours",
            reliability=0.9,
        ),
    ]


class TestHypothesisEvaluation:
    """Tests for deterministic hypothesis evaluation."""

    def test_evaluate_hypothesis_corroborated(self, distributed_evidence):
        evidence_map = {e.id: e for e in distributed_evidence}
        hyp = Hypothesis(
            id="hyp_db_pool",
            title="Database Connection Pool Exhaustion",
            description="Checkout pods exhausted database connections",
            evidence_links=[
                EvidenceLink(evidence_id="ev_alert", relationship=EvidenceRelationshipType.SUPPORTS),
                EvidenceLink(evidence_id="ev_db_log", relationship=EvidenceRelationshipType.SUPPORTS),
            ],
        )
        evaluated = evaluate_hypothesis(hyp, evidence_map)
        assert evaluated.status == HypothesisStatus.STRONGLY_SUPPORTED
        assert evaluated.plausibility_score >= 0.75
        assert evaluated.is_refuted is False
        assert "Corroborated across 2 distinct source types" in evaluated.rationale

    def test_evaluate_hypothesis_refuted_by_contradiction(self, distributed_evidence):
        evidence_map = {e.id: e for e in distributed_evidence}
        # Hypothesis: CPU starvation
        hyp = Hypothesis(
            id="hyp_cpu_spike",
            title="CPU Starvation on Checkout Nodes",
            description="App pods overloaded CPU",
            evidence_links=[
                EvidenceLink(evidence_id="ev_alert", relationship=EvidenceRelationshipType.SUPPORTS),
                EvidenceLink(
                    evidence_id="ev_metric_cpu",
                    relationship=EvidenceRelationshipType.CONTRADICTS,
                    explanation="Metrics prove CPU is idle at 12%",
                ),
            ],
        )
        evaluated = evaluate_hypothesis(hyp, evidence_map)
        assert evaluated.status == HypothesisStatus.REFUTED
        assert evaluated.plausibility_score == 0.0
        assert evaluated.is_refuted is True
        assert "Refuted by 1 contradicting observation" in evaluated.rationale

    def test_evaluate_hypothesis_insufficient_data(self, distributed_evidence):
        evidence_map = {e.id: e for e in distributed_evidence}
        hyp = Hypothesis(
            id="hyp_dns_leak",
            title="DNS Resolver Leak",
            description="Resolver leaking file descriptors",
            evidence_links=[],
        )
        evaluated = evaluate_hypothesis(hyp, evidence_map)
        assert evaluated.status == HypothesisStatus.INSUFFICIENT_DATA
        assert evaluated.plausibility_score < 0.3
        assert "No direct empirical evidence" in evaluated.rationale

    def test_evaluate_hypothesis_unknown_evidence_ref_raises_error(self, distributed_evidence):
        evidence_map = {e.id: e for e in distributed_evidence}
        hyp = Hypothesis(
            id="hyp_test",
            title="Test",
            evidence_links=[
                EvidenceLink(evidence_id="nonexistent_ev", relationship=EvidenceRelationshipType.SUPPORTS)
            ],
        )
        with pytest.raises(ValidationError, match="references unknown evidence"):
            evaluate_hypothesis(hyp, evidence_map)


class TestIncidentInvestigatorCore:
    """Tests for IncidentInvestigator analysis and diagnostic generation."""

    def test_investigator_detects_duplicate_evidence(self, sample_incident):
        investigator = IncidentInvestigator()
        dup_evidence = [
            Evidence(id="ev_1", source_type=EvidenceSourceType.LOGS, summary="Log 1"),
            Evidence(id="ev_1", source_type=EvidenceSourceType.ALERTS, summary="Log 2"),
        ]
        with pytest.raises(ValidationError, match="Duplicate evidence ID"):
            investigator.investigate(sample_incident, dup_evidence)

    def test_competing_hypotheses_ranking_and_tests(self, sample_incident, distributed_evidence):
        investigator = IncidentInvestigator()

        h_db = Hypothesis(
            id="h_db_pool",
            title="Database Connection Pool Exhaustion",
            description="Exhausted DB connection pool",
            root_cause_category="capacity_exhaustion",
            evidence_links=[
                EvidenceLink(evidence_id="ev_alert", relationship=EvidenceRelationshipType.SUPPORTS),
                EvidenceLink(evidence_id="ev_db_log", relationship=EvidenceRelationshipType.SUPPORTS),
            ],
            assumptions=["Pool size configured to 50 connections"],
            unresolved_questions=["Are idle connections leaking?"],
        )
        h_cpu = Hypothesis(
            id="h_cpu_overload",
            title="CPU Overload",
            description="App pods ran out of CPU",
            root_cause_category="hardware_resource",
            evidence_links=[
                EvidenceLink(evidence_id="ev_metric_cpu", relationship=EvidenceRelationshipType.CONTRADICTS),
            ],
        )
        h_dep = Hypothesis(
            id="h_bad_deploy",
            title="Bad Deployment Regression",
            description="Bug deployed to production",
            root_cause_category="configuration_error",
            evidence_links=[
                EvidenceLink(evidence_id="ev_git_deploy", relationship=EvidenceRelationshipType.CONTRADICTS),
            ],
        )

        report = investigator.investigate(
            sample_incident,
            distributed_evidence,
            hypotheses=[h_cpu, h_db, h_dep],
        )

        # H_db should be leading because others are refuted
        assert report.leading_hypothesis_id == "h_db_pool"
        assert report.hypotheses[0].id == "h_db_pool"
        assert report.hypotheses[0].status == HypothesisStatus.STRONGLY_SUPPORTED

        # Other hypotheses must be marked REFUTED
        refuted_ids = [h.id for h in report.hypotheses if h.status == HypothesisStatus.REFUTED]
        assert "h_cpu_overload" in refuted_ids
        assert "h_bad_deploy" in refuted_ids

        # Missing evidence gaps identified
        assert any("Pool size configured" in gap for gap in report.missing_evidence)

        # Proposed confirmation test generated
        assert len(report.proposed_tests) >= 1
        assert "h_db_pool" in report.proposed_tests[0].discriminates_hypotheses

    def test_pairwise_discriminating_tests_for_multiple_unrefuted(self, sample_incident):
        investigator = IncidentInvestigator()
        evidence = [
            Evidence(id="ev_latency", source_type=EvidenceSourceType.METRICS, summary="504 Gateway Timeout"),
        ]

        h1 = Hypothesis(
            id="h1_db",
            title="Database Hang",
            root_cause_category="database",
            evidence_links=[EvidenceLink(evidence_id="ev_latency", relationship=EvidenceRelationshipType.SUPPORTS)],
        )
        h2 = Hypothesis(
            id="h2_redis",
            title="Redis Cache Lock Contention",
            root_cause_category="cache",
            evidence_links=[EvidenceLink(evidence_id="ev_latency", relationship=EvidenceRelationshipType.SUPPORTS)],
        )

        report = investigator.investigate(sample_incident, evidence, hypotheses=[h1, h2])

        # Both remain unrefuted
        assert len([h for h in report.hypotheses if not h.is_refuted]) == 2
        # A discriminating test must exist between h1 and h2
        assert len(report.proposed_tests) >= 1
        discrim = report.proposed_tests[0]
        assert set(discrim.discriminates_hypotheses) == {"h1_db", "h2_redis"}
        assert "h1_db" in discrim.expected_observations
        assert "h2_redis" in discrim.expected_observations
