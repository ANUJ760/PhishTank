"""What-If scenario simulator for Hospital Surgical Theatres and Emergency Departments."""
from __future__ import annotations

import copy
import time

from backend.medops.models import (
    HospitalORPlan,
    HospitalScenarioComparison,
    MedicalStaff,
    OperatingRoom,
    PatientCase,
    WhatIfHospitalDelta,
)
from backend.medops.optimizer import HospitalSurgicalOptimizer
from backend.medops.validator import validate_hospital_plan


class HospitalScenarioSimulator:
    """Simulates mass casualty surges, OR biohazard closures, and staffing disruptions without mutating live state."""

    def __init__(self, optimizer: HospitalSurgicalOptimizer | None = None):
        self.optimizer = optimizer or HospitalSurgicalOptimizer()

    def simulate(
        self,
        baseline_plan: HospitalORPlan,
        hospital_id: str,
        hospital_name: str,
        operating_rooms: list[OperatingRoom],
        staff: list[MedicalStaff],
        patient_cases: list[PatientCase],
        delta: WhatIfHospitalDelta,
        icu_bed_capacity: int = 8,
        horizon_minutes: int = 1440,
        scenario_id: str | None = None,
    ) -> tuple[HospitalORPlan, HospitalScenarioComparison]:
        """Execute counterfactual scenario on isolated deep copies."""
        sim_id = scenario_id or f"SIM-OR-{int(time.time())}"

        sim_rooms = [copy.deepcopy(r) for r in operating_rooms]
        sim_staff = [copy.deepcopy(s) for s in staff]
        sim_cases = [copy.deepcopy(c) for c in patient_cases]

        # 1. Apply OR room closures (e.g. sterile field contamination, equipment repair)
        closed_set = set(delta.decontaminated_or_rooms)
        for r in sim_rooms:
            if r.id in closed_set:
                r.is_operational = False

        # 2. Apply staff call-outs / absences
        unavail_staff_set = set(delta.unavailable_staff)
        for s in sim_staff:
            if s.id in unavail_staff_set:
                s.is_on_duty = False

        # 3. Apply mass casualty surge (add new incoming emergency trauma cases)
        for extra_case in delta.mass_casualty_cases:
            sim_cases.append(copy.deepcopy(extra_case))

        # 4. ICU capacity override
        effective_icu = delta.icu_capacity_override if delta.icu_capacity_override is not None else icu_bed_capacity

        # Run solver on simulation state
        sim_plan = self.optimizer.solve(
            hospital_id=hospital_id,
            hospital_name=hospital_name,
            operating_rooms=sim_rooms,
            staff=sim_staff,
            patient_cases=sim_cases,
            icu_bed_capacity=effective_icu,
            horizon_minutes=horizon_minutes,
            plan_id=sim_id,
            version=baseline_plan.version + 1,
        )

        # Validate simulated plan
        is_valid, violations = validate_hospital_plan(
            plan=sim_plan,
            operating_rooms=sim_rooms,
            staff=sim_staff,
            patient_cases=sim_cases,
            icu_bed_capacity=effective_icu,
        )
        sim_plan.summary.validation_passed = is_valid
        sim_plan.summary.validation_violations = violations

        # Compute side-by-side comparison metrics
        base_summary = baseline_plan.summary
        sim_summary = sim_plan.summary

        wait_time_diff = round(
            sim_summary.mean_emergency_wait_minutes - base_summary.mean_emergency_wait_minutes,
            1,
        )
        bumped_diff = sim_summary.elective_cases_bumped - base_summary.elective_cases_bumped
        resus_diff = round(
            sim_summary.resuscitation_l1_fulfillment - base_summary.resuscitation_l1_fulfillment,
            3,
        )

        # Compare start times of overlapping cases
        base_starts = {item.case_id: item.start_minute for item in baseline_plan.items}
        sim_starts = {item.case_id: item.start_minute for item in sim_plan.items}

        cases_delayed: list[str] = []
        cases_advanced: list[str] = []

        for c_id, b_start in base_starts.items():
            if c_id in sim_starts:
                s_start = sim_starts[c_id]
                if s_start > b_start:
                    cases_delayed.append(c_id)
                elif s_start < b_start:
                    cases_advanced.append(c_id)

        # Build comparison narrative
        narrative_parts = []
        if delta.mass_casualty_cases:
            narrative_parts.append(
                f"Surge of {len(delta.mass_casualty_cases)} mass-casualty emergency patient(s) integrated."
            )
        if delta.decontaminated_or_rooms:
            narrative_parts.append(
                f"Decontamination offline status applied to: {', '.join(delta.decontaminated_or_rooms)}."
            )
        if bumped_diff > 0:
            narrative_parts.append(
                f"+{bumped_diff} additional elective case(s) bumped to clear emergency surgical capacity."
            )
        if wait_time_diff > 0:
            narrative_parts.append(
                f"Mean emergency wait-to-incision increased by +{wait_time_diff} minutes."
            )
        elif wait_time_diff < 0:
            narrative_parts.append(
                f"Mean emergency wait-to-incision reduced by {abs(wait_time_diff)} minutes."
            )

        narrative_text = " ".join(narrative_parts) or "Simulation completed with neutral clinical impact."

        comparison = HospitalScenarioComparison(
            baseline_plan_id=baseline_plan.plan_id,
            simulation_plan_id=sim_plan.plan_id,
            delta_applied=delta,
            wait_time_diff_minutes=wait_time_diff,
            elective_bumped_diff=bumped_diff,
            resuscitation_rate_diff=resus_diff,
            cases_delayed_ids=cases_delayed,
            cases_advanced_ids=cases_advanced,
            summary_text=narrative_text,
        )

        return sim_plan, comparison
