"""Thread-safe registry for MedOps Hospital Emergency Surgical Theatres with realistic benchmark seed."""
from __future__ import annotations

import threading
import time

from backend.medops.models import (
    HospitalORPlan,
    MedicalStaff,
    OperatingRoom,
    PatientCase,
    StaffRole,
    SurgicalSpecialty,
    TriageUrgency,
)


class HospitalORRegistry:
    """State store for Operating Rooms, Surgical Staff, Patient Cases, and OR Plans."""

    def __init__(self):
        self._lock = threading.RLock()
        self.hospital_id = "HOSP-METRO-TRAUMA-1"
        self.hospital_name = "Metro Trauma & Surgical Excellence Center"
        self.icu_bed_capacity = 8

        self.operating_rooms: dict[str, OperatingRoom] = {}
        self.staff: dict[str, MedicalStaff] = {}
        self.patient_cases: dict[str, PatientCase] = {}
        self.plans: dict[str, HospitalORPlan] = {}
        self.latest_plan_id: str | None = None

        self.seed_level1_trauma_benchmark()

    def seed_level1_trauma_benchmark(self) -> None:
        """Seed realistic Level-1 Trauma Surgical Operating Suite scenario."""
        with self._lock:
            self.operating_rooms.clear()
            self.staff.clear()
            self.patient_cases.clear()
            self.plans.clear()
            self.latest_plan_id = None

            # 1. Operating Rooms
            rooms = [
                OperatingRoom(
                    id="OR-TRAUMA-HYBRID",
                    name="OR 1 — Trauma Hybrid Suite",
                    room_type="trauma_hybrid",
                    equipped_capabilities=["c_arm", "rapid_infuser", "laminar_flow", "general"],
                    is_operational=True,
                    turnaround_sterilization_minutes=30,
                ),
                OperatingRoom(
                    id="OR-CARDIAC-SUITE",
                    name="OR 2 — Cardiovascular Theatre",
                    room_type="cardiac_or",
                    equipped_capabilities=["cardiopulmonary_bypass", "laminar_flow", "general"],
                    is_operational=True,
                    turnaround_sterilization_minutes=45,
                ),
                OperatingRoom(
                    id="OR-NEURO-SUITE",
                    name="OR 3 — Neuro-Surgical Theatre",
                    room_type="neuro_suite",
                    equipped_capabilities=["neuro_navigation", "laminar_flow", "general"],
                    is_operational=True,
                    turnaround_sterilization_minutes=40,
                ),
                OperatingRoom(
                    id="OR-ORTHO-SUITE",
                    name="OR 4 — Orthopedic & Spine Theatre",
                    room_type="ortho_suite",
                    equipped_capabilities=["c_arm", "traction_table", "general"],
                    is_operational=True,
                    turnaround_sterilization_minutes=30,
                ),
                OperatingRoom(
                    id="OR-GENERAL-SUITE",
                    name="OR 5 — General Emergency Theatre",
                    room_type="general_or",
                    equipped_capabilities=["laparoscopy", "general"],
                    is_operational=True,
                    turnaround_sterilization_minutes=30,
                ),
            ]
            for r in rooms:
                self.operating_rooms[r.id] = r

            # 2. Medical Staff (Surgeons, Anesthesiologists, Scrub Nurses)
            staff_list = [
                # Lead Surgeons
                MedicalStaff(
                    id="SURG-CHEN",
                    name="Dr. Sarah Chen, MD",
                    role=StaffRole.LEAD_SURGEON,
                    specialties=[SurgicalSpecialty.TRAUMA, SurgicalSpecialty.GENERAL_SURGERY],
                ),
                MedicalStaff(
                    id="SURG-ROSTOVA",
                    name="Dr. Elena Rostova, MD",
                    role=StaffRole.LEAD_SURGEON,
                    specialties=[SurgicalSpecialty.CARDIAC],
                ),
                MedicalStaff(
                    id="SURG-PATEL",
                    name="Dr. Vikram Patel, MD",
                    role=StaffRole.LEAD_SURGEON,
                    specialties=[SurgicalSpecialty.NEUROSURGERY],
                ),
                MedicalStaff(
                    id="SURG-WILSON",
                    name="Dr. James Wilson, MD",
                    role=StaffRole.LEAD_SURGEON,
                    specialties=[SurgicalSpecialty.ORTHOPEDIC, SurgicalSpecialty.TRAUMA],
                ),
                MedicalStaff(
                    id="SURG-LIN",
                    name="Dr. Maya Lin, MD",
                    role=StaffRole.LEAD_SURGEON,
                    specialties=[SurgicalSpecialty.GENERAL_SURGERY, SurgicalSpecialty.TRAUMA],
                ),
                # Anesthesiologists
                MedicalStaff(
                    id="ANES-PENDELTON",
                    name="Dr. Arthur Pendelton, MD",
                    role=StaffRole.ANESTHESIOLOGIST,
                    specialties=[SurgicalSpecialty.CARDIAC, SurgicalSpecialty.TRAUMA],
                ),
                MedicalStaff(
                    id="ANES-DIAZ",
                    name="Dr. Robert Diaz, MD",
                    role=StaffRole.ANESTHESIOLOGIST,
                    specialties=[SurgicalSpecialty.NEUROSURGERY, SurgicalSpecialty.GENERAL_SURGERY],
                ),
                MedicalStaff(
                    id="ANES-KIM",
                    name="Dr. Chloe Kim, MD",
                    role=StaffRole.ANESTHESIOLOGIST,
                    specialties=[SurgicalSpecialty.ORTHOPEDIC, SurgicalSpecialty.GENERAL_SURGERY],
                ),
                # Scrub Nurses
                MedicalStaff(
                    id="NURSE-RAMOS",
                    name="Alex Ramos, RN (Scrub)",
                    role=StaffRole.SCRUB_NURSE,
                ),
                MedicalStaff(
                    id="NURSE-SANTOS",
                    name="Maria Santos, RN (Scrub)",
                    role=StaffRole.SCRUB_NURSE,
                ),
                MedicalStaff(
                    id="NURSE-COOPER",
                    name="David Cooper, RN (Scrub)",
                    role=StaffRole.SCRUB_NURSE,
                ),
                MedicalStaff(
                    id="NURSE-LEE",
                    name="Hannah Lee, RN (Scrub)",
                    role=StaffRole.SCRUB_NURSE,
                ),
            ]
            for s in staff_list:
                self.staff[s.id] = s

            # 3. Patient Cases (Trauma emergencies competing with elective cases)
            cases = [
                # Emergency Resuscitation L1 Cases (Immediate life-threat)
                PatientCase(
                    id="CASE-TRAUMA-01",
                    mrn="MRN-77821",
                    patient_name="John Doe (MVA Trauma)",
                    age=34,
                    triage_urgency=TriageUrgency.RESUSCITATION_L1,
                    specialty=SurgicalSpecialty.TRAUMA,
                    estimated_duration_minutes=150,
                    arrival_minute=0,
                    deadline_minutes=60,
                    required_equipment=["rapid_infuser"],
                    icu_bed_needed=True,
                    clinical_notes="High-speed vehicular crash, acute hemoperitoneum, unstable hemodynamics",
                ),
                PatientCase(
                    id="CASE-CARDIAC-01",
                    mrn="MRN-65412",
                    patient_name="Robert Evans (Aortic Rupture)",
                    age=62,
                    triage_urgency=TriageUrgency.RESUSCITATION_L1,
                    specialty=SurgicalSpecialty.CARDIAC,
                    estimated_duration_minutes=180,
                    arrival_minute=30,
                    deadline_minutes=90,
                    required_equipment=["cardiopulmonary_bypass"],
                    icu_bed_needed=True,
                    clinical_notes="Type A aortic dissection, acute cardiogenic distress",
                ),
                PatientCase(
                    id="CASE-NEURO-01",
                    mrn="MRN-88190",
                    patient_name="Elena Rodriguez (Subdural Hematoma)",
                    age=45,
                    triage_urgency=TriageUrgency.RESUSCITATION_L1,
                    specialty=SurgicalSpecialty.NEUROSURGERY,
                    estimated_duration_minutes=120,
                    arrival_minute=45,
                    deadline_minutes=120,
                    required_equipment=["neuro_navigation"],
                    icu_bed_needed=True,
                    clinical_notes="Acute epidural/subdural hemorrhage with 6mm midline shift",
                ),
                # Emergent L2 Cases (< 2 hour window)
                PatientCase(
                    id="CASE-ORTHO-01",
                    mrn="MRN-92314",
                    patient_name="Marcus Taylor (Open Femur Fracture)",
                    age=28,
                    triage_urgency=TriageUrgency.EMERGENT_L2,
                    specialty=SurgicalSpecialty.ORTHOPEDIC,
                    estimated_duration_minutes=120,
                    arrival_minute=60,
                    deadline_minutes=240,
                    required_equipment=["c_arm"],
                    icu_bed_needed=False,
                    clinical_notes="Gustilo-Anderson Grade IIIB open femoral fracture, active bleeding controlled",
                ),
                PatientCase(
                    id="CASE-GEN-01",
                    mrn="MRN-44109",
                    patient_name="Amina Khan (Perforated Viscus)",
                    age=51,
                    triage_urgency=TriageUrgency.EMERGENT_L2,
                    specialty=SurgicalSpecialty.GENERAL_SURGERY,
                    estimated_duration_minutes=100,
                    arrival_minute=90,
                    deadline_minutes=300,
                    required_equipment=["laparoscopy"],
                    icu_bed_needed=False,
                    clinical_notes="Perforated duodenal ulcer with free air in peritoneum",
                ),
                # Urgent L3 Cases (< 8 hour window)
                PatientCase(
                    id="CASE-GEN-02",
                    mrn="MRN-33120",
                    patient_name="William Chen (Acute Appendicitis)",
                    age=22,
                    triage_urgency=TriageUrgency.URGENT_L3,
                    specialty=SurgicalSpecialty.GENERAL_SURGERY,
                    estimated_duration_minutes=75,
                    arrival_minute=120,
                    deadline_minutes=480,
                    required_equipment=["laparoscopy"],
                    icu_bed_needed=False,
                    clinical_notes="Acute non-perforated suppurative appendicitis",
                ),
                PatientCase(
                    id="CASE-ORTHO-02",
                    mrn="MRN-55182",
                    patient_name="Sarah Jenkins (Septic Knee Joint)",
                    age=59,
                    triage_urgency=TriageUrgency.URGENT_L3,
                    specialty=SurgicalSpecialty.ORTHOPEDIC,
                    estimated_duration_minutes=90,
                    arrival_minute=150,
                    deadline_minutes=600,
                    required_equipment=["c_arm"],
                    icu_bed_needed=False,
                    clinical_notes="Septic arthritis of left knee requiring arthroscopic debridement",
                ),
                # Elective L4 Cases (Scheduled; candidate for bumping under trauma surge)
                PatientCase(
                    id="CASE-ELECT-01",
                    mrn="MRN-10023",
                    patient_name="David Miller (Inguinal Hernia Repair)",
                    age=48,
                    triage_urgency=TriageUrgency.ELECTIVE_L4,
                    specialty=SurgicalSpecialty.GENERAL_SURGERY,
                    estimated_duration_minutes=90,
                    arrival_minute=240,
                    deadline_minutes=None,
                    required_equipment=["general"],
                    icu_bed_needed=False,
                    clinical_notes="Elective bilateral laparoscopic inguinal herniorrhaphy",
                ),
                PatientCase(
                    id="CASE-ELECT-02",
                    mrn="MRN-10088",
                    patient_name="Claire Bennett (Total Knee Arthroplasty)",
                    age=67,
                    triage_urgency=TriageUrgency.ELECTIVE_L4,
                    specialty=SurgicalSpecialty.ORTHOPEDIC,
                    estimated_duration_minutes=120,
                    arrival_minute=300,
                    deadline_minutes=None,
                    required_equipment=["c_arm"],
                    icu_bed_needed=False,
                    clinical_notes="Elective primary right total knee arthroplasty",
                ),
            ]
            for c in cases:
                self.patient_cases[c.id] = c

    def get_rooms(self) -> list[OperatingRoom]:
        with self._lock:
            return list(self.operating_rooms.values())

    def get_staff(self) -> list[MedicalStaff]:
        with self._lock:
            return list(self.staff.values())

    def get_cases(self) -> list[PatientCase]:
        with self._lock:
            return list(self.patient_cases.values())

    def get_case(self, case_id: str) -> PatientCase | None:
        with self._lock:
            return self.patient_cases.get(case_id)

    def save_case(self, case: PatientCase) -> PatientCase:
        with self._lock:
            self.patient_cases[case.id] = case
            return case

    def save_plan(self, plan: HospitalORPlan) -> None:
        with self._lock:
            self.plans[plan.plan_id] = plan
            self.latest_plan_id = plan.plan_id

    def get_latest_plan(self) -> HospitalORPlan | None:
        with self._lock:
            if not self.latest_plan_id:
                return None
            return self.plans.get(self.latest_plan_id)

    def get_plan(self, plan_id: str) -> HospitalORPlan | None:
        with self._lock:
            return self.plans.get(plan_id)


# Global singleton
_hospital_registry: HospitalORRegistry | None = None


def get_hospital_registry() -> HospitalORRegistry:
    global _hospital_registry
    if _hospital_registry is None:
        _hospital_registry = HospitalORRegistry()
    return _hospital_registry
