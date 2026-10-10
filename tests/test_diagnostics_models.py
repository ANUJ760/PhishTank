"""Unit tests for GeCompose diagnostic and alternative models."""

import pytest
from pydantic import ValidationError

from gecompose.models import (
    AlternativeSearchResult,
    ConflictConstraint,
    ConflictDiagnosis,
    ConstraintType,
    RelaxationPolicy,
    RelaxedRequirement,
    ScheduleAlternative,
    ScheduledAssignment,
    SolverStatus,
)


class TestDiagnosticsModels:
    def test_conflict_constraint_creation(self):
        c = ConflictConstraint(
            id="req_pin_slot_sess1",
            constraint_type=ConstraintType.PINNED_SLOT,
            description="Session 'sess1' is pinned to slot 'mon_09'",
            session_id="sess1",
            slot_id="mon_09",
            details={"original_slot": "mon_09"},
        )
        assert c.id == "req_pin_slot_sess1"
        assert c.constraint_type == ConstraintType.PINNED_SLOT
        assert c.session_id == "sess1"
        assert c.slot_id == "mon_09"

    def test_conflict_diagnosis_creation(self):
        diag = ConflictDiagnosis(
            status=SolverStatus.INFEASIBLE,
            is_infeasible=True,
            is_minimal=True,
            conflicting_constraints=[
                ConflictConstraint(
                    id="req_sess_1",
                    constraint_type=ConstraintType.SESSION_REQUIRED,
                    description="Session 's1' must be scheduled",
                    session_id="s1",
                ),
                ConflictConstraint(
                    id="req_t_avail_1",
                    constraint_type=ConstraintType.TEACHER_UNAVAILABLE,
                    description="Prof. Rao is unavailable at Monday 09:00",
                    teacher_id="t1",
                    slot_id="mon_09",
                ),
            ],
            explanation="Session 's1' requires Prof. Rao on Monday 09:00, but Prof. Rao is unavailable at that time.",
            diagnosed_entities={"sessions": ["s1"], "teachers": ["t1"], "slots": ["mon_09"]},
        )
        assert diag.is_infeasible is True
        assert diag.is_minimal is True
        assert diag.has_core is True
        assert len(diag.conflicting_constraints) == 2

    def test_relaxation_policy_defaults_and_validation(self):
        policy = RelaxationPolicy()
        assert policy.allow_slot_relaxation is True
        assert policy.allow_teacher_relaxation is True
        assert policy.allow_room_relaxation is True
        assert policy.max_alternatives == 3
        assert policy.timeout_seconds == 5.0

        with pytest.raises(ValidationError):
            RelaxationPolicy(max_alternatives=0)
        with pytest.raises(ValidationError):
            RelaxationPolicy(timeout_seconds=-1.0)

    def test_alternative_models(self):
        relaxed_req = RelaxedRequirement(
            session_id="s1",
            constraint_type=ConstraintType.PINNED_SLOT,
            original_value="mon_09",
            relaxed_value="mon_10",
            description="Moved session 's1' from mon_09 to mon_10",
        )
        alt = ScheduleAlternative(
            alternative_id=1,
            assignments=[
                ScheduledAssignment(session_id="s1", teacher_id="t1", room_id="r1", slot_id="mon_10")
            ],
            relaxed_requirements=[relaxed_req],
            penalty_score=1,
            validation_passed=True,
            status=SolverStatus.FEASIBLE,
        )
        result = AlternativeSearchResult(
            status=SolverStatus.FEASIBLE,
            original_status=SolverStatus.INFEASIBLE,
            alternatives=[alt],
            search_time_seconds=0.12,
            message="Found 1 alternative schedule",
        )
        assert len(result.alternatives) == 1
        assert result.alternatives[0].relaxed_requirements[0].original_value == "mon_09"
