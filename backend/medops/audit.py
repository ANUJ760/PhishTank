"""Cryptographic SHA-256 audit ledger for MedOps hospital surgical theatre schedules."""
from __future__ import annotations

import hashlib
import json
import time
from typing import Any
from pydantic import BaseModel, Field

from backend.medops.models import HospitalORPlan


class HospitalAuditRecord(BaseModel):
    """Immutable audit trail entry for surgical theatre scheduling events."""
    event_id: str
    event_type: str  # OR_PLAN_OPTIMIZED, OR_PLAN_VALIDATED, OR_PLAN_APPROVED, WHAT_IF_SURGE_SIMULATED
    plan_id: str
    timestamp: float = Field(default_factory=time.time)
    actor: str = "surgical_solver"
    plan_hash: str
    prev_hash: str = "0" * 64
    notes: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)


def compute_hospital_plan_hash(plan: HospitalORPlan) -> str:
    """Compute deterministic SHA-256 canonical hash of a surgical schedule."""
    canonical_obj = {
        "plan_id": plan.plan_id,
        "hospital_id": plan.hospital_id,
        "version": plan.version,
        "solver_status": plan.summary.solver_status,
        "scheduled_cases": plan.summary.scheduled_cases,
        "items": [
            {
                "case_id": item.case_id,
                "patient_mrn": item.patient_mrn,
                "or_room_id": item.or_room_id,
                "start_minute": item.start_minute,
                "end_minute": item.end_minute,
                "lead_surgeon_id": item.lead_surgeon_id,
            }
            for item in sorted(plan.items, key=lambda x: (x.or_room_id, x.start_minute))
        ],
    }
    encoded = json.dumps(canonical_obj, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


class HospitalAuditService:
    """Maintains tamper-evident audit ledger for surgical theatre schedules with SHA-256 verification."""

    def __init__(self):
        self._records: list[HospitalAuditRecord] = []

    def record_plan_creation(
        self,
        plan: HospitalORPlan,
        actor: str = "optimizer",
        notes: str = "CP-SAT surgical schedule generated",
    ) -> HospitalAuditRecord:
        plan_hash = compute_hospital_plan_hash(plan)
        plan.plan_hash = plan_hash
        return self._append_record(
            event_type="OR_PLAN_OPTIMIZED",
            plan_id=plan.plan_id,
            plan_hash=plan_hash,
            actor=actor,
            notes=notes,
            metadata={"solve_time_ms": plan.summary.solve_time_ms},
        )

    def record_validation(
        self,
        plan: HospitalORPlan,
        is_valid: bool,
        violations: list[str],
        actor: str = "validator",
    ) -> HospitalAuditRecord:
        plan_hash = plan.plan_hash or compute_hospital_plan_hash(plan)
        return self._append_record(
            event_type="OR_PLAN_VALIDATED",
            plan_id=plan.plan_id,
            plan_hash=plan_hash,
            actor=actor,
            notes="Passed clinical validation" if is_valid else f"Violations: {'; '.join(violations)}",
            metadata={"passed": is_valid, "violations_count": len(violations)},
        )

    def record_approval(
        self,
        plan: HospitalORPlan,
        approved_by: str,
        notes: str = "Approved by Chief of Surgery",
    ) -> HospitalAuditRecord:
        plan.approved = True
        plan.approved_by = approved_by
        plan_hash = plan.plan_hash or compute_hospital_plan_hash(plan)
        return self._append_record(
            event_type="OR_PLAN_APPROVED",
            plan_id=plan.plan_id,
            plan_hash=plan_hash,
            actor=approved_by,
            notes=notes,
            metadata={"approved_at": time.time()},
        )

    def record_simulation(
        self,
        sim_plan: HospitalORPlan,
        baseline_plan_id: str,
        actor: str = "simulator",
        notes: str = "What-if mass casualty simulation executed",
    ) -> HospitalAuditRecord:
        plan_hash = compute_hospital_plan_hash(sim_plan)
        sim_plan.plan_hash = plan_hash
        return self._append_record(
            event_type="WHAT_IF_SURGE_SIMULATED",
            plan_id=sim_plan.plan_id,
            plan_hash=plan_hash,
            actor=actor,
            notes=notes,
            metadata={"baseline_plan_id": baseline_plan_id},
        )

    def verify_chain_integrity(self) -> tuple[bool, str]:
        """Verify unbroken SHA-256 chain of all hospital audit records."""
        for i, rec in enumerate(self._records):
            if i > 0:
                expected_prev = self._hash_record(self._records[i - 1])
                if rec.prev_hash != expected_prev:
                    return False, f"Broken chain at record {rec.event_id}: expected {expected_prev}, got {rec.prev_hash}"
        return True, "Hospital audit chain intact and cryptographically verified"

    def get_records(self, plan_id: str | None = None) -> list[HospitalAuditRecord]:
        if plan_id:
            return [r for r in self._records if r.plan_id == plan_id]
        return list(self._records)

    def _append_record(
        self,
        event_type: str,
        plan_id: str,
        plan_hash: str,
        actor: str,
        notes: str,
        metadata: dict[str, Any],
    ) -> HospitalAuditRecord:
        prev_hash = "0" * 64
        if self._records:
            prev_hash = self._hash_record(self._records[-1])

        event_id = f"MEDAUDIT-{len(self._records) + 1:04d}-{int(time.time())}"
        record = HospitalAuditRecord(
            event_id=event_id,
            event_type=event_type,
            plan_id=plan_id,
            plan_hash=plan_hash,
            prev_hash=prev_hash,
            actor=actor,
            notes=notes,
            metadata=metadata,
        )
        self._records.append(record)
        return record

    def _hash_record(self, record: HospitalAuditRecord) -> str:
        data = f"{record.event_id}:{record.event_type}:{record.plan_id}:{record.plan_hash}:{record.prev_hash}:{record.timestamp}"
        return hashlib.sha256(data.encode("utf-8")).hexdigest()
