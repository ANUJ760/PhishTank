"""Incident investigation engine for distributed evidence analysis and hypothesis testing."""

from __future__ import annotations

import time
from typing import Any, Sequence

from gecompose.exceptions import ValidationError
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


def evaluate_hypothesis(
    hypothesis: Hypothesis,
    evidence_map: dict[str, Evidence],
) -> Hypothesis:
    """Deterministically evaluate a hypothesis against linked evidence.

    Ensures referential integrity of evidence IDs, computes evidence weights,
    checks for refutations, and produces an unvarnished status verdict with
    justified rationale.

    Args:
        hypothesis: Candidate Hypothesis to evaluate.
        evidence_map: Mapping of known evidence ID -> Evidence object.

    Returns:
        Updated Hypothesis with computed status, plausibility score, and rationale.

    Raises:
        ValidationError: If an evidence link points to an unknown evidence ID.
    """
    for link in hypothesis.evidence_links:
        if link.evidence_id not in evidence_map:
            raise ValidationError(
                f"Hypothesis '{hypothesis.id}' references unknown evidence '{link.evidence_id}'."
            )

    supporting_links = [l for l in hypothesis.evidence_links if l.relationship == EvidenceRelationshipType.SUPPORTS]
    contradicting_links = [l for l in hypothesis.evidence_links if l.relationship == EvidenceRelationshipType.CONTRADICTS]
    inconclusive_links = [l for l in hypothesis.evidence_links if l.relationship == EvidenceRelationshipType.INCONCLUSIVE]

    # Check for direct refutation
    if contradicting_links:
        rebuttal_reasons = [
            f"Evidence '{l.evidence_id}' ({evidence_map[l.evidence_id].summary}): {l.explanation or 'Contradicts premise'}"
            for l in contradicting_links
        ]
        rationale = (
            f"Refuted by {len(contradicting_links)} contradicting observation(s): "
            + "; ".join(rebuttal_reasons)
        )
        return Hypothesis(
            id=hypothesis.id,
            title=hypothesis.title,
            description=hypothesis.description,
            root_cause_category=hypothesis.root_cause_category,
            assumptions=hypothesis.assumptions,
            unresolved_questions=hypothesis.unresolved_questions,
            evidence_links=hypothesis.evidence_links,
            status=HypothesisStatus.REFUTED,
            plausibility_score=0.0,
            rationale=rationale,
        )

    # Check for support
    if supporting_links:
        # Sum weighted support factored by evidence source reliability
        weighted_support = sum(
            link.weight * evidence_map[link.evidence_id].reliability
            for link in supporting_links
        )
        distinct_sources = {
            evidence_map[link.evidence_id].source_type
            for link in supporting_links
        }

        # Epistemological score: multi-source corroboration increases confidence
        # Normalized score between 0.4 and 0.95 (never 1.0 without exhaustive proof)
        source_diversity_bonus = min(0.2, (len(distinct_sources) - 1) * 0.1)
        base_score = min(0.75, 0.50 + (weighted_support * 0.1))
        plausibility = min(0.95, round(base_score + source_diversity_bonus, 3))

        if plausibility >= 0.75 and len(distinct_sources) >= 2:
            status = HypothesisStatus.STRONGLY_SUPPORTED
            rationale = (
                f"Corroborated across {len(distinct_sources)} distinct source types "
                f"({', '.join(s.value for s in distinct_sources)}) with {len(supporting_links)} "
                f"supporting observations. No contradicting evidence found."
            )
        else:
            status = HypothesisStatus.PLAUSIBLE
            rationale = (
                f"Supported by {len(supporting_links)} observation(s) from {len(distinct_sources)} "
                f"source type(s). Remains plausible but requires additional independent verification."
            )

        return Hypothesis(
            id=hypothesis.id,
            title=hypothesis.title,
            description=hypothesis.description,
            root_cause_category=hypothesis.root_cause_category,
            assumptions=hypothesis.assumptions,
            unresolved_questions=hypothesis.unresolved_questions,
            evidence_links=hypothesis.evidence_links,
            status=status,
            plausibility_score=plausibility,
            rationale=rationale,
        )

    # No supporting or contradicting evidence
    rationale = "No direct empirical evidence currently supports or refutes this explanation."
    return Hypothesis(
        id=hypothesis.id,
        title=hypothesis.title,
        description=hypothesis.description,
        root_cause_category=hypothesis.root_cause_category,
        assumptions=hypothesis.assumptions,
        unresolved_questions=hypothesis.unresolved_questions,
        evidence_links=hypothesis.evidence_links,
        status=HypothesisStatus.INSUFFICIENT_DATA,
        plausibility_score=0.2,
        rationale=rationale,
    )


class IncidentInvestigator:
    """AI Incident Investigator engine connecting distributed evidence to competing hypotheses."""

    def __init__(self) -> None:
        pass

    def synthesize_candidate_hypotheses(
        self,
        incident: Incident,
        evidence: Sequence[Evidence],
    ) -> list[Hypothesis]:
        """Generate baseline archetypal hypotheses based on incident context and observed evidence.

        Provides a deterministic starting set of competing failure modes when custom
        hypotheses are not explicitly supplied.
        """
        hypotheses: list[Hypothesis] = []
        comp = incident.affected_component

        # Look for keywords across evidence summaries
        all_text = (
            incident.title + " " + incident.description + " " +
            " ".join(e.summary + " " + str(e.details) for e in evidence)
        ).lower()

        # Archetype 1: Resource / Capacity Starvation
        res_links: list[EvidenceLink] = []
        for e in evidence:
            text = (e.summary + " " + str(e.details)).lower()
            if any(k in text for k in ["cpu", "memory", "pool", "exhaust", "capacity", "timeout", "latency", "504", "queue"]):
                res_links.append(
                    EvidenceLink(
                        evidence_id=e.id,
                        relationship=EvidenceRelationshipType.SUPPORTS,
                        explanation=f"Telemetry indicates resource pressure or timeout symptom: {e.summary}",
                    )
                )
        hypotheses.append(
            Hypothesis(
                id="hyp_resource_exhaustion",
                title=f"Resource Starvation on {comp}",
                description=f"Thread, memory, or connection pool exhaustion in {comp} causing request timeouts.",
                root_cause_category="capacity_exhaustion",
                assumptions=[f"Traffic volume or concurrency spiked", f"Pool limits on {comp} were reached"],
                unresolved_questions=[f"Were worker thread counts or socket pools maxed out?"],
                evidence_links=res_links,
            )
        )

        # Archetype 2: External Dependency / Network Outage
        dep_links: list[EvidenceLink] = []
        for e in evidence:
            text = (e.summary + " " + str(e.details)).lower()
            if any(k in text for k in ["upstream", "network", "dns", "gateway", "remote", "connection refused", "reset by peer"]):
                dep_links.append(
                    EvidenceLink(
                        evidence_id=e.id,
                        relationship=EvidenceRelationshipType.SUPPORTS,
                        explanation=f"Indicates upstream communication failure: {e.summary}",
                    )
                )
        hypotheses.append(
            Hypothesis(
                id="hyp_upstream_dependency_failure",
                title=f"Upstream Dependency Failure for {comp}",
                description=f"Downstream or third-party service dependency unreachable or returning fatal errors.",
                root_cause_category="dependency_failure",
                assumptions=[f"Upstream external provider suffered outage or network partition"],
                unresolved_questions=[f"Can {comp} successfully ping and handshake upstream dependencies?"],
                evidence_links=dep_links,
            )
        )

        # Archetype 3: Bad Configuration or Deployment Regression
        cfg_links: list[EvidenceLink] = []
        for e in evidence:
            text = (e.summary + " " + str(e.details)).lower()
            if any(k in text for k in ["deploy", "config", "release", "commit", "migration", "version", "schema"]):
                cfg_links.append(
                    EvidenceLink(
                        evidence_id=e.id,
                        relationship=EvidenceRelationshipType.SUPPORTS,
                        explanation=f"Correlates with recent environment change: {e.summary}",
                    )
                )
        hypotheses.append(
            Hypothesis(
                id="hyp_configuration_drift_regression",
                title=f"Deployment or Configuration Regression in {comp}",
                description=f"Recent software roll-out or configuration change introduced a functional defect.",
                root_cause_category="configuration_error",
                assumptions=[f"A deployment or parameter change immediately preceded the incident window"],
                unresolved_questions=[f"What was the exact diff between the last known good configuration and current state?"],
                evidence_links=cfg_links,
            )
        )

        return hypotheses

    def identify_missing_evidence(
        self,
        incident: Incident,
        evidence: Sequence[Evidence],
        hypotheses: Sequence[Hypothesis],
    ) -> list[str]:
        """Detect gaps in observational telemetry that prevent conclusive diagnosis."""
        gaps: list[str] = []
        present_types = {e.source_type for e in evidence}

        # Check source coverage
        if EvidenceSourceType.METRICS not in present_types:
            gaps.append(f"No quantitative timeseries metrics (CPU, memory, request rate) collected for {incident.affected_component}.")
        if EvidenceSourceType.LOGS not in present_types:
            gaps.append(f"Application error and trace logs missing for {incident.affected_component}.")
        if EvidenceSourceType.ALERTS not in present_types:
            gaps.append("Automated monitoring alert history for the incident window not attached.")

        # Check unverified assumptions across plausible hypotheses
        for h in hypotheses:
            if not h.is_refuted:
                for assumption in h.assumptions:
                    gaps.append(f"Unverified assumption in '{h.title}': {assumption}")
                for q in h.unresolved_questions:
                    gaps.append(f"Open question for '{h.title}': {q}")

        return gaps

    def propose_diagnostic_tests(
        self,
        incident: Incident,
        hypotheses: Sequence[Hypothesis],
    ) -> list[DiagnosticTest]:
        """Formulate discriminating diagnostic tests to separate unrefuted competing hypotheses."""
        tests: list[DiagnosticTest] = []
        unrefuted = [h for h in hypotheses if not h.is_refuted]

        if len(unrefuted) <= 1:
            # If only one or zero remain unrefuted, propose validation or root-cause confirmation test
            if unrefuted:
                h = unrefuted[0]
                tests.append(
                    DiagnosticTest(
                        id=f"test_confirm_{h.id}",
                        name=f"Confirm {h.title}",
                        purpose=f"Validate hypothesized root cause for {h.title}",
                        target_component=incident.affected_component,
                        procedure=f"Review targeted diagnostics and configuration state for {h.root_cause_category}.",
                        expected_observations={
                            h.id: f"Confirms {h.description}",
                        },
                        discriminates_hypotheses=[h.id],
                        risk_level="low",
                    )
                )
            return tests

        # Generate pairwise discriminating tests
        for i in range(len(unrefuted)):
            for j in range(i + 1, len(unrefuted)):
                h1 = unrefuted[i]
                h2 = unrefuted[j]

                # Craft targeted discriminating probe
                test_id = f"test_diff_{h1.id[:8]}_{h2.id[:8]}"
                tests.append(
                    DiagnosticTest(
                        id=test_id,
                        name=f"Discriminate: {h1.title} vs {h2.title}",
                        purpose=f"Distinguish between {h1.root_cause_category} and {h2.root_cause_category}",
                        target_component=incident.affected_component,
                        procedure=(
                            f"Execute isolated reachability and dependency probe on {incident.affected_component}; "
                            f"inspect local connection pool utilization vs upstream socket response."
                        ),
                        expected_observations={
                            h1.id: f"Observation specific to {h1.title} (e.g. local queue saturation)",
                            h2.id: f"Observation specific to {h2.title} (e.g. upstream timeout or config mismatch)",
                        },
                        discriminates_hypotheses=[h1.id, h2.id],
                        risk_level="low",
                    )
                )

        return tests

    def investigate(
        self,
        incident: Incident,
        evidence: Sequence[Evidence],
        hypotheses: Sequence[Hypothesis] | None = None,
    ) -> InvestigationReport:
        """Execute a full, traceable incident investigation.

        1. Validates and maps empirical evidence repository.
        2. Evaluates candidate hypotheses against evidence.
        3. Separates supported explanations from refuted failure modes.
        4. Identifies missing evidence and unverified assumptions.
        5. Proposes discriminating diagnostic tests.
        6. Generates a structured InvestigationReport.

        Args:
            incident: Target Incident under investigation.
            evidence: Chronological repository of observed facts.
            hypotheses: Optional explicit candidate hypotheses. If None, archetypes
                are automatically synthesized from incident context and evidence.

        Returns:
            Comprehensive InvestigationReport.
        """
        # Build evidence map
        evidence_map: dict[str, Evidence] = {}
        for e in evidence:
            if e.id in evidence_map:
                raise ValidationError(f"Duplicate evidence ID '{e.id}' detected.")
            evidence_map[e.id] = e

        # Determine candidate hypotheses
        candidates = list(hypotheses) if hypotheses is not None else self.synthesize_candidate_hypotheses(incident, evidence)

        # Evaluate every hypothesis
        evaluated_hypotheses = [evaluate_hypothesis(h, evidence_map) for h in candidates]

        # Sort hypotheses by status and plausibility score descending
        # Non-refuted first, then by score
        def sort_key(h: Hypothesis) -> tuple[int, float]:
            refuted_rank = 0 if not h.is_refuted else 1
            return (refuted_rank, -h.plausibility_score)

        sorted_hypotheses = sorted(evaluated_hypotheses, key=sort_key)

        # Identify leading hypothesis
        unrefuted = [h for h in sorted_hypotheses if not h.is_refuted]
        leading_hypothesis_id = unrefuted[0].id if unrefuted and unrefuted[0].plausibility_score > 0.3 else None

        # Detect missing evidence gaps
        missing = self.identify_missing_evidence(incident, evidence, sorted_hypotheses)

        # Propose diagnostic tests
        proposed_tests = self.propose_diagnostic_tests(incident, sorted_hypotheses)

        # Synthesize confidence assessment
        if not unrefuted:
            assessment = "All candidate hypotheses have been refuted by contradicting evidence. Root cause remains unidentified."
            inv_status = IncidentStatus.INVESTIGATING
        elif len(unrefuted) == 1:
            h = unrefuted[0]
            assessment = (
                f"Single viable explanation identified: '{h.title}' (score {h.plausibility_score}). "
                f"Requires confirmation via recommended diagnostic tests."
            )
            inv_status = IncidentStatus.IDENTIFIED if h.status == HypothesisStatus.STRONGLY_SUPPORTED else IncidentStatus.INVESTIGATING
        else:
            assessment = (
                f"Multiple competing explanations remain plausible ({len(unrefuted)} unrefuted). "
                f"Leading candidate is '{unrefuted[0].title}' (score {unrefuted[0].plausibility_score}), "
                f"but discriminating diagnostic tests must be executed to rule out alternatives."
            )
            inv_status = IncidentStatus.INVESTIGATING

        return InvestigationReport(
            incident=incident,
            hypotheses=sorted_hypotheses,
            evidence_trail=list(evidence),
            missing_evidence=missing,
            proposed_tests=proposed_tests,
            leading_hypothesis_id=leading_hypothesis_id,
            confidence_assessment=assessment,
            investigation_status=inv_status,
            statistics={
                "total_evidence": len(evidence),
                "total_hypotheses": len(sorted_hypotheses),
                "refuted_hypotheses": len([h for h in sorted_hypotheses if h.is_refuted]),
                "unrefuted_hypotheses": len(unrefuted),
                "proposed_tests_count": len(proposed_tests),
            },
        )
