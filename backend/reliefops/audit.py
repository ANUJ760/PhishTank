"""Audit and traceability ledger recording allocation plans, validations, and approvals."""
from __future__ import annotations

import hashlib
import json
import time
from typing import Any
from pydantic import BaseModel, Field

from backend.reliefops.models import AllocationPlan


class AuditRecord(BaseModel):
    """Immutable audit trail entry for ReliefOps decision tracing."""
    event_id: str
    event_type: str  # PLAN_CREATED, PLAN_VALIDATED, PLAN_APPROVED, WHAT_IF_SIMULATED
    plan_id: str
    timestamp: float = Field(default_factory=time.time)
    actor: str = "system"
    plan_hash: str
    prev_hash: str = "0" * 64
    notes: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)


def compute_plan_hash(plan: AllocationPlan) -> str:
    """Compute deterministic SHA-256 canonical hash of an allocation plan."""
    # Build clean canonical dictionary
    canonical_obj = {
        "plan_id": plan.plan_id,
        "incident_id": plan.incident_id,
        "version": plan.version,
        "solver_status": plan.summary.solver_status,
        "overall_fulfillment_rate": plan.summary.overall_fulfillment_rate,
        "allocations": [
            {
                "camp_id": a.camp_id,
                "resource_id": a.resource_id,
                "requested": a.requested_quantity,
                "allocated": a.allocated_quantity,
                "unmet": a.unmet_quantity,
            }
            for a in sorted(plan.allocations, key=lambda x: (x.camp_id, x.resource_id))
        ],
    }
    encoded = json.dumps(canonical_obj, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


class AuditService:
    """Manages immutable audit log of disaster allocations with SHA-256 verification."""

    def __init__(self):
        self._records: list[AuditRecord] = []

    def record_plan_creation(
        self,
        plan: AllocationPlan,
        actor: str = "optimizer",
        notes: str = "Optimization completed",
    ) -> AuditRecord:
        plan_hash = compute_plan_hash(plan)
        plan.plan_hash = plan_hash
        return self._append_record(
            event_type="PLAN_CREATED",
            plan_id=plan.plan_id,
            plan_hash=plan_hash,
            actor=actor,
            notes=notes,
            metadata={"solve_time_ms": plan.summary.solve_time_ms},
        )

    def record_validation(
        self,
        plan: AllocationPlan,
        is_valid: bool,
        violations: list[str],
        actor: str = "validator",
    ) -> AuditRecord:
        plan_hash = plan.plan_hash or compute_plan_hash(plan)
        return self._append_record(
            event_type="PLAN_VALIDATED",
            plan_id=plan.plan_id,
            plan_hash=plan_hash,
            actor=actor,
            notes="Passed validation" if is_valid else f"Violations: {'; '.join(violations)}",
            metadata={"passed": is_valid, "violations_count": len(violations)},
        )

    def record_approval(
        self,
        plan: AllocationPlan,
        approved_by: str,
        notes: str = "Approved by commander",
    ) -> AuditRecord:
        plan.approved = True
        plan.approved_by = approved_by
        plan_hash = plan.plan_hash or compute_plan_hash(plan)
        return self._append_record(
            event_type="PLAN_APPROVED",
            plan_id=plan.plan_id,
            plan_hash=plan_hash,
            actor=approved_by,
            notes=notes,
            metadata={"approved_at": time.time()},
        )

    def record_simulation(
        self,
        sim_plan: AllocationPlan,
        baseline_plan_id: str,
        actor: str = "simulator",
        notes: str = "What-if simulation executed",
    ) -> AuditRecord:
        plan_hash = compute_plan_hash(sim_plan)
        sim_plan.plan_hash = plan_hash
        return self._append_record(
            event_type="WHAT_IF_SIMULATED",
            plan_id=sim_plan.plan_id,
            plan_hash=plan_hash,
            actor=actor,
            notes=notes,
            metadata={"baseline_plan_id": baseline_plan_id},
        )

    def verify_chain_integrity(self) -> tuple[bool, str]:
        """Verify unbroken SHA-256 chain of all audit events."""
        for i, rec in enumerate(self._records):
            if i > 0:
                expected_prev = self._hash_record(self._records[i - 1])
                if rec.prev_hash != expected_prev:
                    return False, f"Broken chain at record {rec.event_id}: expected {expected_prev}, got {rec.prev_hash}"
        return True, "Audit chain intact and verified"

    def get_records(self, plan_id: str | None = None) -> list[AuditRecord]:
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
    ) -> AuditRecord:
        prev_hash = "0" * 64
        if self._records:
            prev_hash = self._hash_record(self._records[-1])

        event_id = f"AUDIT-{len(self._records) + 1:04d}-{int(time.time())}"
        record = AuditRecord(
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

    def _hash_record(self, record: AuditRecord) -> str:
        data = f"{record.event_id}:{record.event_type}:{record.plan_id}:{record.plan_hash}:{record.prev_hash}:{record.timestamp}"
        return hashlib.sha256(data.encode("utf-8")).hexdigest()
