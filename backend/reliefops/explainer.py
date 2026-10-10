"""Explainable AI decision service for ReliefOps allocations using Gemma 12B reasoning."""
from __future__ import annotations

import logging
from typing import Any
from pydantic import BaseModel, Field

from backend import config
from backend.llm.gemma import GemmaService, get_gemma_service
from backend.reliefops.models import AllocationPlan, ReliefCamp, ResourceType

log = logging.getLogger(__name__)


class PlanExplanation(BaseModel):
    """Structured, human-readable audit and commander explanation of an allocation plan."""
    plan_id: str
    scenario_id: str
    overview: str
    key_findings: list[str] = Field(default_factory=list)
    critical_needs_assessment: str = ""
    bottleneck_resources: list[str] = Field(default_factory=list)
    trade_off_rationale: str = ""
    recommendations_for_command: list[str] = Field(default_factory=list)
    camp_explanations: dict[str, str] = Field(default_factory=dict)


class AllocationExplainer:
    """Generates transparent, auditable rationales distinguishing hard constraints from priority trade-offs."""

    def __init__(self, gemma_service: GemmaService | None = None):
        self.gemma = gemma_service or get_gemma_service()

    def generate_explanation(
        self,
        plan: AllocationPlan,
        camps: list[ReliefCamp],
        resources: list[ResourceType],
    ) -> PlanExplanation:
        """Produce an explainable rationale for the optimization result."""
        summary = plan.summary
        camp_map = {c.id: c for c in camps}
        res_map = {r.id: r for r in resources}

        # Identify bottlenecks: resources where total available < total requested
        bottlenecks = [
            r_id
            for r_id, avail in summary.total_available.items()
            if avail < summary.total_requested.get(r_id, 0)
        ]

        # Check if LLM should be skipped (e.g. MOCK_LLM)
        if config.MOCK_LLM:
            return self._build_deterministic_explanation(plan, camps, resources, bottlenecks)

        prompt_data = {
            "scenario_id": summary.scenario_id,
            "solver_status": summary.solver_status,
            "overall_fulfillment_rate": f"{summary.overall_fulfillment_rate * 100:.1f}%",
            "critical_fulfillment_rate": f"{summary.critical_fulfillment_rate * 100:.1f}%",
            "fairness_index": f"{summary.fairness_index * 100:.1f}%",
            "bottlenecks": bottlenecks,
            "total_requested": summary.total_requested,
            "total_allocated": summary.total_allocated,
            "total_unmet": summary.total_unmet,
            "camps": [
                {
                    "id": c.id,
                    "name": c.name,
                    "population": c.population,
                    "vulnerable": c.vulnerable_population,
                    "access": c.access_status,
                }
                for c in camps
            ],
            "shortages": summary.unresolved_shortages[:8],
        }

        messages = [
            {
                "role": "system",
                "content": (
                    "You are the Lead Disaster Operations Logistics Intelligence Officer using Gemma 12B. "
                    "Analyze this CP-SAT emergency supply allocation plan. Provide an objective, transparent, "
                    "and explainable diagnostic distinguishing hard physical constraints (vehicle access, warehouse stock, camp storage) "
                    "from ethical/priority trade-offs (vulnerable population weighting, critical urgency protection). "
                    "Return strictly valid JSON conforming to the requested schema."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Please analyze this disaster relief allocation data:\n\n"
                    f"{prompt_data}\n\n"
                    f"Required JSON schema:\n"
                    f"{PlanExplanation.model_json_schema()}"
                ),
            },
        ]

        try:
            explanation, _ = self.gemma.generate_json(
                tier="12b",
                messages=messages,
                schema=PlanExplanation,
                retries=1,
            )
            # Ensure plan_id and scenario_id match
            explanation.plan_id = plan.plan_id
            explanation.scenario_id = summary.scenario_id
            return explanation
        except Exception as exc:
            log.warning("Gemma 12B explanation failed (%s), falling back to deterministic explanation", exc)
            return self._build_deterministic_explanation(plan, camps, resources, bottlenecks)

    def _build_deterministic_explanation(
        self,
        plan: AllocationPlan,
        camps: list[ReliefCamp],
        resources: list[ResourceType],
        bottlenecks: list[str],
    ) -> PlanExplanation:
        """Deterministic rule-based explanation engine when LLM is in mock mode or unavailable."""
        summary = plan.summary
        camp_map = {c.id: c for c in camps}
        res_map = {r.id: r for r in resources}

        overview = (
            f"Allocation plan '{summary.name}' resolved with solver status '{summary.solver_status}' "
            f"in {summary.solve_time_ms} ms. The system achieved {summary.overall_fulfillment_rate * 100:.1f}% "
            f"overall supply fulfillment, with {summary.critical_fulfillment_rate * 100:.1f}% of life-critical "
            f"demands satisfied across {len(camps)} relief camps."
        )

        key_findings = [
            f"Overall demand fulfillment is {summary.overall_fulfillment_rate * 100:.1f}%.",
            f"Critical life-support fulfillment is {summary.critical_fulfillment_rate * 100:.1f}%.",
            f"Maximin fairness index across camps is {summary.fairness_index * 100:.1f}%.",
        ]

        if bottlenecks:
            key_findings.append(
                f"Severe inventory scarcity identified for: {', '.join(bottlenecks)}."
            )
        else:
            key_findings.append("Regional inventory is sufficient to meet current requested volume.")

        crit_assessment = (
            f"Life-critical requests (medical kits and drinking water) were given lexicographic priority. "
            f"The critical fulfillment rate is {summary.critical_fulfillment_rate * 100:.1f}%. "
            f"Non-critical supplies were rationed proportionally to preserve safety margins."
        )

        trade_offs = (
            "Hard physical constraints strictly enforced: available warehouse inventory limits, vehicle terrain "
            "accessibility (air/boat/road), and camp storage volume/weight limits. "
            "Optimization objective minimized weighted unmet demand, giving highest precedence to camps with "
            "elevated vulnerable populations and severe shortages."
        )

        recommendations = []
        if bottlenecks:
            recommendations.append(
                f"Emergency resupply requested: Deploy inter-agency procurement for scarce resources ({', '.join(bottlenecks)})."
            )
        for camp in camps:
            if camp.access_status in ("air_only", "boat_only"):
                recommendations.append(
                    f"Maintain dedicated {camp.access_status.replace('_', ' ')} transport corridors for {camp.name}."
                )
        if not recommendations:
            recommendations.append("Continue monitoring camp inventory and schedule next regular dispatch window.")

        # Camp-by-camp explanations
        camp_explanations: dict[str, str] = {}
        for camp in camps:
            c_allocs = [a for a in plan.allocations if a.camp_id == camp.id]
            req_sum = sum(a.requested_quantity for a in c_allocs)
            alloc_sum = sum(a.allocated_quantity for a in c_allocs)
            c_ratio = alloc_sum / req_sum if req_sum > 0 else 1.0

            unmet_items = [
                f"{a.resource_name} ({a.unmet_quantity} unmet)"
                for a in c_allocs
                if a.unmet_quantity > 0
            ]
            if not unmet_items:
                camp_explanations[camp.id] = (
                    f"{camp.name} (Pop: {camp.population}): 100% fulfilled ({alloc_sum} units). "
                    f"All requested supplies allocated successfully."
                )
            else:
                camp_explanations[camp.id] = (
                    f"{camp.name} (Pop: {camp.population}, Access: {camp.access_status}): "
                    f"{c_ratio * 100:.1f}% fulfilled ({alloc_sum}/{req_sum} units). "
                    f"Rationed supplies: {', '.join(unmet_items)}. Shortages driven by regional scarcity and vehicle capacities."
                )

        return PlanExplanation(
            plan_id=plan.plan_id,
            scenario_id=summary.scenario_id,
            overview=overview,
            key_findings=key_findings,
            critical_needs_assessment=crit_assessment,
            bottleneck_resources=bottlenecks,
            trade_off_rationale=trade_offs,
            recommendations_for_command=recommendations,
            camp_explanations=camp_explanations,
        )
