#!/usr/bin/env python3
"""
demo_investigation.py — GeCompose AI Incident Investigation Engine demo.

Scenario
--------
The payment-service has been returning HTTP 504 Gateway Timeout errors since
13:15 UTC.  Three competing explanations exist:

  H1  Database connection-pool exhaustion (strongly supported)
  H2  Upstream gateway misconfiguration  (refuted by metrics)
  H3  Config/deployment regression       (refuted by change log)

The engine evaluates every hypothesis against the available evidence,
identifies missing evidence gaps, and proposes discriminating diagnostic
tests that would let an on-call engineer distinguish any remaining
unrefuted hypotheses.

Run
---
    .venv/bin/python examples/demo_investigation.py
"""

from __future__ import annotations

import json
import textwrap

from gecompose import (
    Evidence,
    EvidenceRelationshipType,
    EvidenceSourceType,
    Hypothesis,
    Incident,
    IncidentSeverity,
    IncidentStatus,
    investigate_incident,
    serialize_result,
)

# ---------------------------------------------------------------------------
# 1. Define the incident
# ---------------------------------------------------------------------------

incident = Incident(
    id="INC-2026-1010-001",
    title="Payment Service — HTTP 504 Gateway Timeout",
    description=(
        "Payment service endpoints /api/pay and /api/refund have been returning "
        "HTTP 504 errors since 13:15 UTC.  Downstream services (cart, checkout) "
        "are degraded.  No scheduled maintenance window is active."
    ),
    affected_component="payment-service",
    severity=IncidentSeverity.HIGH,
    status=IncidentStatus.INVESTIGATING,
    start_time="2026-10-10T13:15:00Z",
    end_time="2026-10-10T13:30:00Z",
)

# ---------------------------------------------------------------------------
# 2. Collect distributed evidence
# ---------------------------------------------------------------------------

# Application logs
log_pool_exhausted = Evidence(
    id="EVD-001",
    source_type=EvidenceSourceType.LOGS,
    summary="HikariPool-1: Connection is not available, request timed out after 30000ms. Pool size: 10/10 active.",
    timestamp="2026-10-10T13:16:22Z",
    source_ref="payment-service/app.log",
    reliability=0.95,
)

log_query_slow = Evidence(
    id="EVD-002",
    source_type=EvidenceSourceType.LOGS,
    summary="Slow query detected: SELECT * FROM transactions WHERE ... took 28400ms (threshold: 500ms).",
    timestamp="2026-10-10T13:17:05Z",
    source_ref="payment-service/app.log",
    reliability=0.90,
)

log_no_deploy = Evidence(
    id="EVD-003",
    source_type=EvidenceSourceType.LOGS,
    summary="CI/CD pipeline: no deployments to production in the past 6 hours. Last successful deploy: 2026-10-09T22:41Z (v3.4.1).",
    timestamp="2026-10-10T12:00:00Z",
    source_ref="ci-cd/pipeline.log",
    reliability=0.99,
)

# Alerts
alert_db_connections = Evidence(
    id="EVD-004",
    source_type=EvidenceSourceType.ALERTS,
    summary="CRITICAL — payment-db: active_connections=98/100 (98%). Alert fired at threshold 90%.",
    timestamp="2026-10-10T13:15:45Z",
    source_ref="alertmanager/payment-db",
    reliability=0.97,
)

alert_gateway_ok = Evidence(
    id="EVD-005",
    source_type=EvidenceSourceType.ALERTS,
    summary="INFO — api-gateway: all routing rules validated. No configuration drift detected in the last 2 hours.",
    timestamp="2026-10-10T13:20:00Z",
    source_ref="alertmanager/api-gateway",
    reliability=0.92,
)

# Metrics
metric_db_cpu = Evidence(
    id="EVD-006",
    source_type=EvidenceSourceType.METRICS,
    summary="payment-db CPU: 94% (1-min avg). I/O wait: 62%. Disk throughput: 450 MB/s (normal peak: 80 MB/s).",
    timestamp="2026-10-10T13:18:00Z",
    source_ref="prometheus/payment-db",
    reliability=0.98,
)

metric_gateway_latency = Evidence(
    id="EVD-007",
    source_type=EvidenceSourceType.METRICS,
    summary="api-gateway p99 latency: 42ms (baseline: 38ms). No anomaly detected in gateway routing layer.",
    timestamp="2026-10-10T13:18:30Z",
    source_ref="prometheus/api-gateway",
    reliability=0.95,
)

all_evidence = [
    log_pool_exhausted,
    log_query_slow,
    log_no_deploy,
    alert_db_connections,
    alert_gateway_ok,
    metric_db_cpu,
    metric_gateway_latency,
]

# ---------------------------------------------------------------------------
# 3. Define competing hypotheses with evidence links
# ---------------------------------------------------------------------------

h1_db_pool = Hypothesis(
    id="HYP-001",
    title="Database connection-pool exhaustion",
    description=(
        "A spike in slow queries has saturated the DB connection pool. "
        "New requests cannot acquire a connection within the timeout window, "
        "causing the service to return 504s upstream."
    ),
    root_cause_category="database",
    assumptions=[
        "No recent schema migration increased query cost",
        "Connection-pool size has not been recently reduced",
    ],
    evidence_links=[
        {
            "evidence_id": "EVD-001",
            "relationship": EvidenceRelationshipType.SUPPORTS,
            "weight": 1.0,
            "explanation": "Pool exhaustion log directly confirms connection starvation.",
        },
        {
            "evidence_id": "EVD-002",
            "relationship": EvidenceRelationshipType.SUPPORTS,
            "weight": 0.9,
            "explanation": "Slow-query log corroborates that DB overload is the bottleneck.",
        },
        {
            "evidence_id": "EVD-004",
            "relationship": EvidenceRelationshipType.SUPPORTS,
            "weight": 1.0,
            "explanation": "98/100 active-connection alert confirms pool saturation from a second source.",
        },
        {
            "evidence_id": "EVD-006",
            "relationship": EvidenceRelationshipType.SUPPORTS,
            "weight": 0.85,
            "explanation": "94% CPU + 62% I/O wait on payment-db confirms heavy database load.",
        },
    ],
)

h2_gateway_misconfig = Hypothesis(
    id="HYP-002",
    title="Upstream gateway misconfiguration",
    description=(
        "A gateway routing rule was misconfigured, causing requests to be "
        "forwarded to a stale or non-existent backend endpoint."
    ),
    root_cause_category="network",
    assumptions=[
        "Gateway configuration was recently modified",
    ],
    evidence_links=[
        {
            "evidence_id": "EVD-005",
            "relationship": EvidenceRelationshipType.CONTRADICTS,
            "weight": 1.0,
            "explanation": "Gateway config-OK alert confirms no routing drift — refutes this hypothesis.",
        },
        {
            "evidence_id": "EVD-007",
            "relationship": EvidenceRelationshipType.CONTRADICTS,
            "weight": 0.9,
            "explanation": "Nominal gateway latency (42ms) rules out a routing-layer failure.",
        },
    ],
)

h3_config_regression = Hypothesis(
    id="HYP-003",
    title="Config or deployment regression",
    description=(
        "A recent deployment introduced a configuration change (e.g., reduced "
        "pool size or wrong DB hostname) that degraded the payment service."
    ),
    root_cause_category="config",
    assumptions=[
        "A deployment occurred within the incident window",
    ],
    evidence_links=[
        {
            "evidence_id": "EVD-003",
            "relationship": EvidenceRelationshipType.CONTRADICTS,
            "weight": 0.99,
            "explanation": "CI/CD log confirms no deployments in the past 6 hours — refutes regression hypothesis.",
        },
    ],
)

all_hypotheses = [h1_db_pool, h2_gateway_misconfig, h3_config_regression]

# ---------------------------------------------------------------------------
# 4. Run the investigation
# ---------------------------------------------------------------------------

report = investigate_incident(
    incident=incident,
    evidence=all_evidence,
    hypotheses=all_hypotheses,
)

# ---------------------------------------------------------------------------
# 5. Display results
# ---------------------------------------------------------------------------

DIVIDER = "─" * 70


def _wrap(text: str, indent: int = 4) -> str:
    prefix = " " * indent
    return textwrap.fill(
        text, width=78, initial_indent=prefix, subsequent_indent=prefix
    )


print(f"\n{'=' * 70}")
print("  GeCompose — AI Incident Investigation Engine Demo")
print(f"{'=' * 70}\n")

# Incident summary
print(f"INCIDENT  {incident.id}")
print(f"  Title    : {incident.title}")
print(f"  Severity : {incident.severity.value.upper()}")
print(f"  Status   : {incident.status.value}")
print(f"  Window   : {incident.start_time} – {incident.end_time}")
print(f"  Component: {incident.affected_component}")

# Report summary
print(f"\n{DIVIDER}")
print(f"INVESTIGATION REPORT")
print(f"  Evidence collected     : {report.total_evidence_count}")
print(f"  Hypotheses evaluated   : {report.total_hypotheses_count}")
print(f"  Has unrefuted hypothesis: {report.has_unrefuted_hypothesis}")
print(f"  Leading hypothesis     : {report.leading_hypothesis_id}")
print(f"  Investigation status   : {report.investigation_status.value}")
print()
print(_wrap(f"Confidence assessment: {report.confidence_assessment}"))

# Hypothesis verdicts
print(f"\n{DIVIDER}")
print("HYPOTHESIS VERDICTS")
STATUS_ICONS = {
    "strongly_supported": "✅",
    "supported": "🟡",
    "refuted": "❌",
    "insufficient_data": "❓",
    "plausible": "🔵",
}
for hyp in report.hypotheses:
    icon = STATUS_ICONS.get(hyp.status.value, "•")
    print(f"\n  {icon}  [{hyp.id}] {hyp.title}")
    print(f"      Status       : {hyp.status.value}")
    print(f"      Plausibility : {hyp.plausibility_score:.3f}  (heuristic, range 0.0–0.95)")
    print(f"      Supporting   : {len(hyp.supporting_evidence_ids)} — {hyp.supporting_evidence_ids}")
    print(f"      Contradicting: {len(hyp.contradicting_evidence_ids)} — {hyp.contradicting_evidence_ids}")
    print(f"      Refuted      : {hyp.is_refuted}")
    if hyp.rationale:
        print(_wrap(f"Rationale: {hyp.rationale}"))

# Missing evidence gaps
print(f"\n{DIVIDER}")
print(f"MISSING EVIDENCE GAPS  ({len(report.missing_evidence)} identified)")
if report.missing_evidence:
    for i, gap in enumerate(report.missing_evidence, 1):
        print(f"\n  {i}. {gap}")
else:
    print("  None — sufficient evidence coverage across all source types.")

# Proposed diagnostic tests
print(f"\n{DIVIDER}")
print(f"PROPOSED DIAGNOSTIC TESTS  ({len(report.proposed_tests)} proposed)")
if report.proposed_tests:
    for test in report.proposed_tests:
        print(f"\n  [{test.id}]  {test.name}")
        print(f"    Purpose   : {test.purpose}")
        print(f"    Component : {test.target_component}")
        print(f"    Risk      : {test.risk_level}")
        print(_wrap(f"Procedure: {test.procedure}"))
        if test.discriminates_hypotheses:
            print(f"    Discriminates: {test.discriminates_hypotheses}")
        if test.expected_observations:
            for hid, obs in test.expected_observations.items():
                print(f"    If {hid} true: {obs}")
else:
    print("  No tests proposed (single decisive outcome).")

# Statistics
print(f"\n{DIVIDER}")
print("STATISTICS")
for k, v in report.statistics.items():
    print(f"  {k}: {v}")

# JSON serialization
print(f"\n{DIVIDER}")
print("JSON SERIALIZATION  (first 1 400 chars)")
as_dict = serialize_result(report)
as_json = json.dumps(as_dict, indent=2, default=str)
print(as_json[:1400])
if len(as_json) > 1400:
    print(f"  ... [{len(as_json) - 1400} chars truncated] ...")

print(f"\n{'=' * 70}")
print("  Demo complete — all results are deterministic and fully serializable.")
print(f"{'=' * 70}\n")
