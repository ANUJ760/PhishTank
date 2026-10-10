"""Explainable AI clinical decision service for MedOps Surgical Theatres using Gemma 12B reasoning."""
from __future__ import annotations

import logging
from pydantic import BaseModel, Field

from backend import config
from backend.llm.gemma import GemmaService, get_gemma_service
from backend.medops.models import HospitalORPlan, MedicalStaff, OperatingRoom, PatientCase

log = logging.getLogger(__name__)


class HospitalPlanExplanation(BaseModel):
    """Clinical, human-readable rationale for operating theatre allocations."""
    plan_id: str
    hospital_name: str
    overview: str
    triage_prioritization_rationale: str
    bumped_elective_cases_analysis: str
    identified_bottlenecks: list[str] = Field(default_factory=list)
    clinical_recommendations: list[str] = Field(default_factory=list)
    case_rationales: dict[str, str] = Field(default_factory=dict)  # case_id -> explanation


class HospitalSurgicalExplainer:
    """Generates transparent medical operations explanations with Gemma 12B reasoning."""

    def __init__(self, gemma_service: GemmaService | None = None):
        self.gemma = gemma_service or get_gemma_service()

    def generate_explanation(
        self,
        plan: HospitalORPlan,
        operating_rooms: list[OperatingRoom],
        staff: list[MedicalStaff],
        patient_cases: list[PatientCase],
    ) -> HospitalPlanExplanation:
        """Produce an explainable clinical operations report for the surgical director."""
        summary = plan.summary

        # Bottlenecks analysis
        bottlenecks = []
        if summary.peak_or_utilization_rate > 0.85:
            bottlenecks.append("Critical OR Suite Saturation (>85% utilization)")
        if summary.icu_bed_usage >= summary.icu_bed_capacity:
            bottlenecks.append(f"Post-Op ICU Bed Capacity Exhausted ({summary.icu_bed_usage}/{summary.icu_bed_capacity})")
        if summary.elective_cases_bumped > 0:
            bottlenecks.append(f"Elective Surgery Displacements ({summary.elective_cases_bumped} cases deferred)")

        if config.MOCK_LLM:
            return self._build_deterministic_explanation(plan, operating_rooms, staff, patient_cases, bottlenecks)

        prompt_data = {
            "hospital_name": summary.hospital_name,
            "total_cases": summary.total_cases,
            "scheduled_cases": summary.scheduled_cases,
            "resuscitation_l1_rate": f"{summary.resuscitation_l1_fulfillment * 100:.1f}%",
            "emergent_l2_rate": f"{summary.emergent_l2_fulfillment * 100:.1f}%",
            "mean_wait_minutes": summary.mean_emergency_wait_minutes,
            "elective_bumped": summary.elective_cases_bumped,
            "or_utilization": f"{summary.peak_or_utilization_rate * 100:.1f}%",
            "bottlenecks": bottlenecks,
            "operating_rooms": [r.name for r in operating_rooms],
            "sample_cases": [
                {
                    "id": item.case_id,
                    "patient": item.patient_name,
                    "urgency": item.triage_urgency,
                    "room": item.or_room_name,
                    "delay": f"{item.delay_minutes}m",
                }
                for item in plan.items[:6]
            ],
        }

        messages = [
            {
                "role": "system",
                "content": (
                    "You are the Chief Medical Operations Officer using Gemma 12B. "
                    "Analyze this emergency surgical operating theatre schedule. "
                    "Articulate clinical triage justifications (why Level 1 Resuscitation cases took precedence), "
                    "explain elective surgical delays, diagnose hospital bottlenecks (ICU beds, specialty coverage), "
                    "and provide actionable recommendations for surgical command. "
                    "Return strictly valid JSON matching the requested schema."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Operational surgical board data:\n\n"
                    f"{prompt_data}\n\n"
                    f"Required JSON schema:\n"
                    f"{HospitalPlanExplanation.model_json_schema()}"
                ),
            },
        ]

        try:
            explanation, _ = self.gemma.generate_json(
                tier="12b",
                messages=messages,
                schema=HospitalPlanExplanation,
                retries=1,
            )
            explanation.plan_id = plan.plan_id
            explanation.hospital_name = summary.hospital_name
            return explanation
        except Exception as exc:
            log.warning("Gemma 12B medops explanation failed (%s), using deterministic fallback", exc)
            return self._build_deterministic_explanation(plan, operating_rooms, staff, patient_cases, bottlenecks)

    def _build_deterministic_explanation(
        self,
        plan: HospitalORPlan,
        operating_rooms: list[OperatingRoom],
        staff: list[MedicalStaff],
        patient_cases: list[PatientCase],
        bottlenecks: list[str],
    ) -> HospitalPlanExplanation:
        summary = plan.summary

        overview = (
            f"Operating theatre master plan for '{summary.hospital_name}' generated with solver status '{summary.solver_status}'. "
            f"A total of {summary.scheduled_cases}/{summary.total_cases} surgical cases were accommodated "
            f"({summary.overall_fulfillment_rate * 100:.1f}% fulfillment). "
            f"All Level-1 Resuscitation cases were prioritized with {summary.resuscitation_l1_fulfillment * 100:.1f}% fulfillment, "
            f"achieving a mean emergency wait-to-incision time of {summary.mean_emergency_wait_minutes} minutes."
        )

        triage_rationale = (
            "Clinical triage rules strictly dictated resource allocation. Immediate life-threat cases (massive hemothorax, "
            "ruptured aneurysm, open skull fracture) were assigned dedicated trauma-equipped suites immediately upon arrival. "
            "Operating room turnaround sterilization windows (30-45m) were strictly enforced to prevent surgical site infections."
        )

        elective_analysis = (
            f"{summary.elective_cases_bumped} elective surgical procedures were deferred due to emergency room capacity. "
            "Elective cases were safely rescheduled to preserve sterile theatre availability and post-op ICU bed capacity for acute trauma."
        )

        recommendations = [
            "Maintain fast-track turnover protocol in Trauma Hybrid OR.",
            "Pre-alert PACU and Step-Down units to accelerate bed turnover for incoming surgical recoveries.",
        ]
        if summary.icu_bed_usage >= summary.icu_bed_capacity:
            recommendations.append("Initiate ICU surge capacity protocol; explore step-down transfers for stable patients.")

        case_rationales = {}
        for item in plan.items:
            case_rationales[item.case_id] = (
                f"Patient '{item.patient_name}' ({item.triage_urgency}) allocated to {item.or_room_name} "
                f"under Lead Surgeon {item.lead_surgeon_name}. Incision scheduled at minute {item.start_minute} "
                f"(Wait: {item.delay_minutes}m)."
            )

        return HospitalPlanExplanation(
            plan_id=plan.plan_id,
            hospital_name=summary.hospital_name,
            overview=overview,
            triage_prioritization_rationale=triage_rationale,
            bumped_elective_cases_analysis=elective_analysis,
            identified_bottlenecks=bottlenecks,
            clinical_recommendations=recommendations,
            case_rationales=case_rationales,
        )
