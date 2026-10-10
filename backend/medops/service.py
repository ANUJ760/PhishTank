"""High-level orchestration service for MedOps Hospital Surgical Theatre & Operating Room Optimizer."""
from __future__ import annotations

import logging
from typing import Any

from backend.medops.audit import HospitalAuditRecord, HospitalAuditService
from backend.medops.explainer import HospitalPlanExplanation, HospitalSurgicalExplainer
from backend.medops.intake import HospitalIntakeService
from backend.medops.models import (
    HospitalORPlan,
    HospitalScenarioComparison,
    PatientCase,
    WhatIfHospitalDelta,
)
from backend.medops.optimizer import HospitalSurgicalOptimizer
from backend.medops.registry import HospitalORRegistry, get_hospital_registry
from backend.medops.simulator import HospitalScenarioSimulator
from backend.medops.validator import validate_hospital_plan

log = logging.getLogger(__name__)


class MedOpsService:
    """Production-grade Hospital Emergency Surgical Theatre and OR Coordination Facade."""

    def __init__(
        self,
        registry: HospitalORRegistry | None = None,
        optimizer: HospitalSurgicalOptimizer | None = None,
        simulator: HospitalScenarioSimulator | None = None,
        explainer: HospitalSurgicalExplainer | None = None,
        intake: HospitalIntakeService | None = None,
        audit: HospitalAuditService | None = None,
    ):
        self.registry = registry or get_hospital_registry()
        self.optimizer = optimizer or HospitalSurgicalOptimizer()
        self.simulator = simulator or HospitalScenarioSimulator(self.optimizer)
        self.explainer = explainer or HospitalSurgicalExplainer()
        self.intake = intake or HospitalIntakeService()
        self.audit = audit or HospitalAuditService()

    def get_overview(self) -> dict[str, Any]:
        """Return high-level summary of active hospital surgical status and latest master plan."""
        latest_plan = self.registry.get_latest_plan()
        rooms = self.registry.get_rooms()
        staff = self.registry.get_staff()
        cases = self.registry.get_cases()

        active_rooms = sum(1 for r in rooms if r.is_operational)
        active_staff = sum(1 for s in staff if s.is_on_duty)
        emergency_cases = sum(1 for c in cases if c.triage_urgency in (1, 2))
        elective_cases = sum(1 for c in cases if c.triage_urgency == 4)

        return {
            "hospital_id": self.registry.hospital_id,
            "hospital_name": self.registry.hospital_name,
            "operating_rooms_count": len(rooms),
            "operational_rooms_count": active_rooms,
            "medical_staff_count": len(staff),
            "active_staff_count": active_staff,
            "total_patient_cases": len(cases),
            "emergency_cases_count": emergency_cases,
            "elective_cases_count": elective_cases,
            "icu_bed_capacity": self.registry.icu_bed_capacity,
            "has_master_plan": latest_plan is not None,
            "latest_plan_id": latest_plan.plan_id if latest_plan else None,
            "latest_plan_approved": latest_plan.approved if latest_plan else False,
            "resuscitation_fulfillment_rate": latest_plan.summary.resuscitation_l1_fulfillment if latest_plan else 0.0,
            "overall_fulfillment_rate": latest_plan.summary.overall_fulfillment_rate if latest_plan else 0.0,
        }

    def optimize_schedule(self, plan_id: str | None = None) -> HospitalORPlan:
        """Run CP-SAT surgical solver, validate clinical invariants, record in audit ledger, and save."""
        rooms = self.registry.get_rooms()
        staff = self.registry.get_staff()
        cases = self.registry.get_cases()

        plan = self.optimizer.solve(
            hospital_id=self.registry.hospital_id,
            hospital_name=self.registry.hospital_name,
            operating_rooms=rooms,
            staff=staff,
            patient_cases=cases,
            icu_bed_capacity=self.registry.icu_bed_capacity,
            plan_id=plan_id,
        )

        # Independent clinical validation
        is_valid, violations = validate_hospital_plan(
            plan=plan,
            operating_rooms=rooms,
            staff=staff,
            patient_cases=cases,
            icu_bed_capacity=self.registry.icu_bed_capacity,
        )
        plan.summary.validation_passed = is_valid
        plan.summary.validation_violations = violations

        # Record in cryptographic audit ledger
        self.audit.record_plan_creation(plan, actor="surgical_optimizer", notes="OR CP-SAT schedule generated")
        self.audit.record_validation(plan, is_valid=is_valid, violations=violations, actor="clinical_validator")

        # Save in registry
        self.registry.save_plan(plan)
        return plan

    def run_simulation(
        self,
        delta: WhatIfHospitalDelta,
        scenario_id: str | None = None,
    ) -> tuple[HospitalORPlan, HospitalScenarioComparison]:
        """Execute counterfactual surgical simulation without mutating live hospital state."""
        baseline_plan = self.registry.get_latest_plan()
        if not baseline_plan:
            baseline_plan = self.optimize_schedule()

        sim_plan, comparison = self.simulator.simulate(
            baseline_plan=baseline_plan,
            hospital_id=self.registry.hospital_id,
            hospital_name=self.registry.hospital_name,
            operating_rooms=self.registry.get_rooms(),
            staff=self.registry.get_staff(),
            patient_cases=self.registry.get_cases(),
            delta=delta,
            icu_bed_capacity=self.registry.icu_bed_capacity,
            scenario_id=scenario_id,
        )

        self.audit.record_simulation(
            sim_plan=sim_plan,
            baseline_plan_id=baseline_plan.plan_id,
            actor="hospital_simulator",
            notes=f"Simulated surge: +{len(delta.mass_casualty_cases)} trauma patients, "
                  f"{len(delta.decontaminated_or_rooms)} offline OR rooms",
        )

        self.registry.save_plan(sim_plan)
        return sim_plan, comparison

    def explain_schedule(self, plan_id: str | None = None) -> HospitalPlanExplanation:
        """Produce Gemma 12B clinical operational explanation."""
        plan = self.registry.get_plan(plan_id) if plan_id else self.registry.get_latest_plan()
        if not plan:
            plan = self.optimize_schedule()

        return self.explainer.generate_explanation(
            plan=plan,
            operating_rooms=self.registry.get_rooms(),
            staff=self.registry.get_staff(),
            patient_cases=self.registry.get_cases(),
        )

    def approve_schedule(
        self,
        plan_id: str,
        approved_by: str,
        notes: str = "Chief of Surgery sign-off",
    ) -> HospitalAuditRecord:
        """Independently validate and authorize surgical theatre schedule."""
        plan = self.registry.get_plan(plan_id)
        if not plan:
            raise LookupError(f"Hospital plan '{plan_id}' not found")

        if not plan.summary.validation_passed:
            raise ValueError(
                f"Cannot approve invalid surgical schedule: clinical violations detected ({'; '.join(plan.summary.validation_violations)})"
            )

        return self.audit.record_approval(plan, approved_by=approved_by, notes=notes)

    def intake_csv(self, csv_data: str | bytes) -> list[PatientCase]:
        """Ingest surgical waitlist from CSV."""
        cases = self.intake.parse_csv_cases(csv_data)
        for c in cases:
            self.registry.save_case(c)
        return cases

    def intake_dispatch(self, dispatch_text: str) -> list[PatientCase]:
        """Ingest incoming trauma dispatch using Gemma 4B."""
        cases = self.intake.extract_from_clinical_dispatch(dispatch_text)
        for c in cases:
            self.registry.save_case(c)
        return cases


# Global singleton
_medops_service: MedOpsService | None = None


def get_medops_service() -> MedOpsService:
    global _medops_service
    if _medops_service is None:
        _medops_service = MedOpsService()
    return _medops_service
