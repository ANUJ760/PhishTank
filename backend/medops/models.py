"""Strongly-typed domain models for MedOps Hospital Emergency Surgical Theatre Optimizer."""
from __future__ import annotations

from enum import Enum, IntEnum
import time
from typing import Any
from pydantic import BaseModel, Field


class TriageUrgency(IntEnum):
    """Emergency Severity Index (ESI) surgical urgency levels."""
    RESUSCITATION_L1 = 1   # Immediate life/limb threat (< 15 min): aortic rupture, brain bleed, penetrating trauma
    EMERGENT_L2 = 2        # High risk (< 60 min): ruptured appendix, open fracture, compartment syndrome
    URGENT_L3 = 3          # Urgent (< 6 hours): bowel obstruction, acute gallbladder, septic joint
    ELECTIVE_L4 = 4        # Elective / non-emergency: scheduled arthroplasty, hernia repair, cosmetic reconstruction


class SurgicalSpecialty(str, Enum):
    TRAUMA = "trauma"
    CARDIAC = "cardiac"
    NEUROSURGERY = "neurosurgery"
    ORTHOPEDIC = "orthopedic"
    GENERAL_SURGERY = "general"
    PEDIATRIC = "pediatric"


class StaffRole(str, Enum):
    LEAD_SURGEON = "lead_surgeon"
    ANESTHESIOLOGIST = "anesthesiologist"
    SCRUB_NURSE = "scrub_nurse"
    PERFUSIONIST = "perfusionist"


class OperatingRoom(BaseModel):
    """Surgical operating theatre with equipment capabilities and decontamination rules."""
    id: str
    name: str
    room_type: str = "general_or"  # trauma_hybrid, cardiac_or, neuro_suite, general_or
    equipped_capabilities: list[str] = Field(default_factory=list)  # bypass, c_arm, laminar_flow, rapid_infuser
    is_operational: bool = True
    turnaround_sterilization_minutes: int = 30  # Mandatory sterilization before next patient
    max_duration_hours: float = 24.0


class MedicalStaff(BaseModel):
    """Surgical specialists, anesthesiologists, and trauma nurses."""
    id: str
    name: str
    role: StaffRole
    specialties: list[SurgicalSpecialty] = Field(default_factory=list)
    is_on_duty: bool = True
    max_consecutive_minutes: int = 480  # 8 hour shift limit
    current_fatigue_minutes: int = 0


class PatientCase(BaseModel):
    """Patient requiring surgical intervention with clinical urgency and timeline."""
    id: str
    mrn: str  # Medical Record Number
    patient_name: str
    age: int
    triage_urgency: TriageUrgency
    specialty: SurgicalSpecialty
    estimated_duration_minutes: int
    arrival_minute: int = 0  # Minute of the day (0 = 00:00, 480 = 08:00)
    deadline_minutes: int | None = None  # Clinical maximum time-to-incision
    required_equipment: list[str] = Field(default_factory=list)
    icu_bed_needed: bool = False
    clinical_notes: str = ""
    status: str = "pending"  # pending, scheduled, in_surgery, completed, bumped
    created_at: float = Field(default_factory=time.time)


class SurgicalScheduleItem(BaseModel):
    """Scheduled surgical slot in an operating theatre with assigned clinical team."""
    case_id: str
    patient_mrn: str
    patient_name: str
    triage_urgency: str
    specialty: str
    or_room_id: str
    or_room_name: str
    start_minute: int
    end_minute: int
    sterilization_end_minute: int
    lead_surgeon_id: str
    lead_surgeon_name: str
    anesthesiologist_id: str
    anesthesiologist_name: str
    scrub_nurse_id: str
    delay_minutes: int
    deadline_breached: bool
    icu_reserved: bool
    clinical_rationale: str
    enforced_constraints: list[str] = Field(default_factory=list)


class HospitalORSummary(BaseModel):
    """Macro performance metrics for operating theatre utilization and emergency responsiveness."""
    plan_id: str
    hospital_name: str
    solver_status: str  # optimal, feasible, infeasible
    solve_time_ms: int
    total_cases: int
    scheduled_cases: int
    emergency_cases_handled: int
    elective_cases_bumped: int
    overall_fulfillment_rate: float
    resuscitation_l1_fulfillment: float
    emergent_l2_fulfillment: float
    mean_emergency_wait_minutes: float
    peak_or_utilization_rate: float
    icu_bed_usage: int
    icu_bed_capacity: int
    validation_passed: bool
    validation_violations: list[str] = Field(default_factory=list)
    shortages_and_delays: list[dict[str, Any]] = Field(default_factory=list)
    created_at: float = Field(default_factory=time.time)


class HospitalORPlan(BaseModel):
    """Master operating theatre schedule verified under clinical and physical invariants."""
    plan_id: str
    hospital_id: str
    version: int = 1
    summary: HospitalORSummary
    items: list[SurgicalScheduleItem]
    approved: bool = False
    approved_by: str | None = None
    plan_hash: str = ""
    created_at: float = Field(default_factory=time.time)


class WhatIfHospitalDelta(BaseModel):
    """Counterfactual scenario for hospital mass casualty or OR disruption."""
    mass_casualty_cases: list[PatientCase] = Field(default_factory=list)
    decontaminated_or_rooms: list[str] = Field(default_factory=list)  # Offline OR rooms
    unavailable_staff: list[str] = Field(default_factory=list)        # Absent surgeons/anesthesiologists
    icu_capacity_override: int | None = None


class HospitalScenarioComparison(BaseModel):
    """Side-by-side analysis of surgical theatre counterfactual against baseline."""
    baseline_plan_id: str
    simulation_plan_id: str
    delta_applied: WhatIfHospitalDelta
    wait_time_diff_minutes: float
    elective_bumped_diff: int
    resuscitation_rate_diff: float
    cases_delayed_ids: list[str] = Field(default_factory=list)
    cases_advanced_ids: list[str] = Field(default_factory=list)
    summary_text: str
