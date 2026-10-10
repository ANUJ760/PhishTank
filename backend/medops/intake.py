"""Intake and triage consolidation service for MedOps surgical cases supporting CSV and AI extraction."""
from __future__ import annotations

import csv
import io
import logging
import time
import uuid
from typing import Any
from pydantic import BaseModel, Field

from backend import config
from backend.llm.gemma import GemmaService, get_gemma_service
from backend.medops.models import PatientCase, SurgicalSpecialty, TriageUrgency

log = logging.getLogger(__name__)


class ExtractedClinicalCase(BaseModel):
    """Schema for individual emergency surgical request parsed by Gemma 4B."""
    patient_name: str = "Emergency Trauma Patient"
    age: int = 40
    specialty: str = "trauma"
    triage_level: str = "RESUSCITATION_L1"  # RESUSCITATION_L1, EMERGENT_L2, URGENT_L3, ELECTIVE_L4
    duration_minutes: int = 120
    required_equipment: list[str] = Field(default_factory=list)
    icu_required: bool = False
    clinical_notes: str = ""


class ClinicalDispatchExtractionResult(BaseModel):
    """Consolidated response from Gemma 4B medical dispatch parser."""
    cases: list[ExtractedClinicalCase] = Field(default_factory=list)
    triage_summary: str = ""


class HospitalIntakeService:
    """Consolidates hospital surgical requests from CSV rosters, EHR notes, and paramedic radio calls."""

    def __init__(self, gemma_service: GemmaService | None = None):
        self.gemma = gemma_service or get_gemma_service()

    def parse_csv_cases(self, csv_content: str | bytes) -> list[PatientCase]:
        """Parse tabular surgical booking waitlist or emergency add-on cases."""
        if isinstance(csv_content, bytes):
            text = csv_content.decode("utf-8-sig", errors="replace")
        else:
            text = csv_content

        reader = csv.DictReader(io.StringIO(text))
        cases: list[PatientCase] = []

        for i, row in enumerate(reader, start=1):
            mrn = str(row.get("mrn", row.get("patient_mrn", f"MRN-{uuid.uuid4().hex[:6].upper()}"))).strip()
            name = str(row.get("patient_name", row.get("name", f"Patient {i}"))).strip()
            try:
                age = max(1, int(float(row.get("age", 45))))
            except (ValueError, TypeError):
                age = 45

            specialty_str = str(row.get("specialty", "general")).strip().lower()
            specialty = self._parse_specialty(specialty_str)

            urgency_str = str(row.get("triage", row.get("urgency", "URGENT_L3"))).strip().upper()
            urgency = self._parse_urgency(urgency_str)

            try:
                dur = max(30, int(float(row.get("duration", row.get("duration_minutes", 90)))))
            except (ValueError, TypeError):
                dur = 90

            try:
                arrival = max(0, int(float(row.get("arrival_minute", row.get("arrival", 0)))))
            except (ValueError, TypeError):
                arrival = 0

            try:
                deadline_raw = row.get("deadline_minutes", row.get("deadline"))
                deadline = int(float(deadline_raw)) if deadline_raw else None
            except (ValueError, TypeError):
                deadline = None

            equip_str = str(row.get("required_equipment", row.get("equipment", "")))
            equip = [e.strip() for e in equip_str.split(";") if e.strip()] if equip_str else []

            icu_needed = str(row.get("icu_bed_needed", row.get("icu", "false"))).lower() in ("true", "1", "yes")
            notes = str(row.get("clinical_notes", row.get("notes", ""))).strip()

            case = PatientCase(
                id=f"CASE-CSV-{i}-{uuid.uuid4().hex[:6]}",
                mrn=mrn,
                patient_name=name,
                age=age,
                triage_urgency=urgency,
                specialty=specialty,
                estimated_duration_minutes=dur,
                arrival_minute=arrival,
                deadline_minutes=deadline,
                required_equipment=equip,
                icu_bed_needed=icu_needed,
                clinical_notes=notes or f"Imported via CSV waitlist entry #{i}",
                status="pending",
                created_at=time.time(),
            )
            cases.append(case)

        return cases

    def extract_from_clinical_dispatch(self, dispatch_text: str) -> list[PatientCase]:
        """Extract structured PatientCase models from paramedic radio dispatches using Gemma 4B."""
        if config.MOCK_LLM:
            return self._heuristic_clinical_extraction(dispatch_text)

        messages = [
            {
                "role": "system",
                "content": (
                    "You are a Hospital Emergency Medical Triage Specialist using Gemma 4B. "
                    "Extract structured surgical emergency cases from paramedic radio transmissions, ambulance notes, or trauma dispatches. "
                    "Determine triage level (RESUSCITATION_L1, EMERGENT_L2, URGENT_L3, ELECTIVE_L4), "
                    "surgical specialty, estimated surgical duration, and equipment needs. "
                    "Return strictly valid JSON conforming to the requested schema."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Incoming medical dispatch transmission:\n\"\"\"{dispatch_text}\"\"\"\n\n"
                    f"Extract into JSON matching schema:\n"
                    f"{ClinicalDispatchExtractionResult.model_json_schema()}"
                ),
            },
        ]

        try:
            extraction, _ = self.gemma.generate_json(
                tier="4b",
                messages=messages,
                schema=ClinicalDispatchExtractionResult,
                retries=1,
            )
            cases: list[PatientCase] = []
            for item in extraction.cases:
                cases.append(
                    PatientCase(
                        id=f"CASE-AI-{uuid.uuid4().hex[:8]}",
                        mrn=f"MRN-EMERG-{uuid.uuid4().hex[:6].upper()}",
                        patient_name=item.patient_name,
                        age=item.age,
                        triage_urgency=self._parse_urgency(item.triage_level),
                        specialty=self._parse_specialty(item.specialty),
                        estimated_duration_minutes=max(30, item.duration_minutes),
                        arrival_minute=0,
                        required_equipment=item.required_equipment,
                        icu_bed_needed=item.icu_required,
                        clinical_notes=item.clinical_notes or f"Extracted via Gemma 4B: {dispatch_text[:70]}...",
                        status="pending",
                        created_at=time.time(),
                    )
                )
            if cases:
                return cases
            return self._heuristic_clinical_extraction(dispatch_text)
        except Exception as exc:
            log.warning("Gemma 4B clinical extraction failed (%s), using heuristic parser", exc)
            return self._heuristic_clinical_extraction(dispatch_text)

    def _heuristic_clinical_extraction(self, text: str) -> list[PatientCase]:
        """Deterministic heuristic clinical parser for offline test verification."""
        t_lower = text.lower()
        urgency = TriageUrgency.URGENT_L3
        if any(w in t_lower for w in ["resuscitation", "massive", "gunshot", "penetrating", "hemorrhage", "rupture", "cardiac arrest", "code blue"]):
            urgency = TriageUrgency.RESUSCITATION_L1
        elif any(w in t_lower for w in ["emergent", "open fracture", "acute", "compartment", "appendix"]):
            urgency = TriageUrgency.EMERGENT_L2

        specialty = SurgicalSpecialty.GENERAL_SURGERY
        if any(w in t_lower for w in ["heart", "cardiac", "aorta", "bypass", "valve"]):
            specialty = SurgicalSpecialty.CARDIAC
        elif any(w in t_lower for w in ["brain", "skull", "craniotomy", "neuro", "subdural"]):
            specialty = SurgicalSpecialty.NEUROSURGERY
        elif any(w in t_lower for w in ["bone", "fracture", "ortho", "femur", "pelvis"]):
            specialty = SurgicalSpecialty.ORTHOPEDIC
        elif any(w in t_lower for w in ["trauma", "stab", "accident", "mva"]):
            specialty = SurgicalSpecialty.TRAUMA

        equip = []
        if specialty == SurgicalSpecialty.CARDIAC:
            equip.append("cardiopulmonary_bypass")
        elif specialty == SurgicalSpecialty.ORTHOPEDIC:
            equip.append("c_arm")

        case = PatientCase(
            id=f"CASE-HEUR-{uuid.uuid4().hex[:8]}",
            mrn=f"MRN-TRAUMA-{uuid.uuid4().hex[:6].upper()}",
            patient_name="Emergency Trauma Arrival",
            age=38,
            triage_urgency=urgency,
            specialty=specialty,
            estimated_duration_minutes=120 if urgency == TriageUrgency.RESUSCITATION_L1 else 90,
            arrival_minute=0,
            required_equipment=equip,
            icu_bed_needed=urgency in (TriageUrgency.RESUSCITATION_L1, TriageUrgency.EMERGENT_L2),
            clinical_notes=f"Heuristic intake from dispatch: {text[:80]}",
            status="pending",
        )
        return [case]

    def _parse_specialty(self, val: str) -> SurgicalSpecialty:
        v = val.strip().lower()
        for spec in SurgicalSpecialty:
            if spec.value in v or v in spec.value:
                return spec
        return SurgicalSpecialty.GENERAL_SURGERY

    def _parse_urgency(self, val: str) -> TriageUrgency:
        v = val.strip().upper()
        if "RESUSC" in v or "1" in v:
            return TriageUrgency.RESUSCITATION_L1
        if "EMERG" in v or "2" in v:
            return TriageUrgency.EMERGENT_L2
        if "URG" in v or "3" in v:
            return TriageUrgency.URGENT_L3
        if "ELECT" in v or "4" in v:
            return TriageUrgency.ELECTIVE_L4
        return TriageUrgency.URGENT_L3
