"""GeCompose MedOps — Hospital Emergency Operating Theatre & Surgical Suite Optimizer."""
from __future__ import annotations

from backend.medops.audit import HospitalAuditRecord, HospitalAuditService, compute_hospital_plan_hash
from backend.medops.explainer import HospitalPlanExplanation, HospitalSurgicalExplainer
from backend.medops.intake import HospitalIntakeService
from backend.medops.models import (
    HospitalORPlan,
    HospitalORSummary,
    HospitalScenarioComparison,
    MedicalStaff,
    OperatingRoom,
    PatientCase,
    StaffRole,
    SurgicalScheduleItem,
    SurgicalSpecialty,
    TriageUrgency,
    WhatIfHospitalDelta,
)
from backend.medops.optimizer import HospitalSurgicalOptimizer
from backend.medops.registry import HospitalORRegistry, get_hospital_registry
from backend.medops.service import MedOpsService, get_medops_service
from backend.medops.simulator import HospitalScenarioSimulator
from backend.medops.validator import HospitalValidationError, validate_hospital_plan

__all__ = [
    "HospitalAuditRecord",
    "HospitalAuditService",
    "HospitalIntakeService",
    "HospitalORPlan",
    "HospitalORRegistry",
    "HospitalORSummary",
    "HospitalScenarioComparison",
    "HospitalScenarioSimulator",
    "HospitalSurgicalExplainer",
    "HospitalSurgicalOptimizer",
    "HospitalValidationError",
    "MedicalStaff",
    "MedOpsService",
    "OperatingRoom",
    "PatientCase",
    "StaffRole",
    "SurgicalScheduleItem",
    "SurgicalSpecialty",
    "TriageUrgency",
    "WhatIfHospitalDelta",
    "compute_hospital_plan_hash",
    "get_hospital_registry",
    "get_hospital_service",
    "get_medops_service",
    "validate_hospital_plan",
]
