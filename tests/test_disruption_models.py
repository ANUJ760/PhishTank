"""Tests for disruption and recovery data models."""

from __future__ import annotations

import pytest
from gecompose.models import (
    AssignmentChange,
    DisruptionEvent,
    DisruptionRecoveryResult,
    ImpactReport,
    RecoveryPolicy,
    ResourceType,
    ScheduledAssignment,
    SchedulingProblem,
    SolverStatus,
    TimeSlot,
)


def test_disruption_event_creation_with_slot_ids():
    event = DisruptionEvent(
        id="disp_1",
        resource_type=ResourceType.ROOM,
        resource_id="room_101",
        slot_ids={"slot_1", "slot_2"},
        reason="Water leak",
    )
    assert event.id == "disp_1"
    assert event.resource_type == ResourceType.ROOM
    assert event.resource_id == "room_101"
    assert event.slot_ids == {"slot_1", "slot_2"}
    assert event.reason == "Water leak"


def test_disruption_event_creation_with_interval():
    event = DisruptionEvent(
        id="disp_2",
        resource_type=ResourceType.TEACHER,
        resource_id="t_1",
        day="Monday",
        start_time="09:00",
        end_time="11:30",
        reason="Medical emergency",
    )
    assert event.day == "Monday"
    assert event.start_time == "09:00"
    assert event.end_time == "11:30"


def test_disruption_event_rejects_empty_ids():
    with pytest.raises(ValueError, match="cannot be empty"):
        DisruptionEvent(
            id="   ",
            resource_type=ResourceType.ROOM,
            resource_id="r1",
            slot_ids={"s1"},
        )

    with pytest.raises(ValueError, match="cannot be empty"):
        DisruptionEvent(
            id="d1",
            resource_type=ResourceType.ROOM,
            resource_id="",
            slot_ids={"s1"},
        )


def test_disruption_event_rejects_missing_interval_or_slots():
    with pytest.raises(ValueError, match="must specify either 'slot_ids' or a valid time interval"):
        DisruptionEvent(
            id="d1",
            resource_type=ResourceType.ROOM,
            resource_id="r1",
        )


def test_disruption_event_rejects_inverted_time():
    with pytest.raises(ValueError, match="must be strictly after start_time"):
        DisruptionEvent(
            id="d1",
            resource_type=ResourceType.ROOM,
            resource_id="r1",
            day="Monday",
            start_time="11:00",
            end_time="10:00",
        )


def test_disruption_event_rejects_partial_interval():
    with pytest.raises(ValueError, match="'day', 'start_time', and 'end_time' must all be provided"):
        DisruptionEvent(
            id="d1",
            resource_type=ResourceType.ROOM,
            resource_id="r1",
            day="Monday",
            start_time="10:00",
            # missing end_time
        )


def test_resolve_unavailable_slots():
    problem = SchedulingProblem(
        slots=[
            TimeSlot(id="s1", day="Monday", start_time="09:00", end_time="10:00"),
            TimeSlot(id="s2", day="Monday", start_time="10:00", end_time="11:00"),
            TimeSlot(id="s3", day="Tuesday", start_time="09:00", end_time="10:00"),
        ]
    )
    event = DisruptionEvent(
        id="d1",
        resource_type=ResourceType.ROOM,
        resource_id="r1",
        day="Monday",
        start_time="09:30",
        end_time="10:30",
    )
    # Overlaps s1 (09:00-10:00) and s2 (10:00-11:00)
    resolved = event.resolve_unavailable_slots(problem)
    assert resolved == {"s1", "s2"}


def test_impact_report_properties():
    event = DisruptionEvent(
        id="d1",
        resource_type=ResourceType.ROOM,
        resource_id="r1",
        slot_ids={"s1"},
    )
    report = ImpactReport(
        disruption=event,
        directly_affected_session_ids=["sess_1"],
        directly_affected_assignments=[
            ScheduledAssignment(session_id="sess_1", teacher_id="t1", room_id="r1", slot_id="s1")
        ],
        unaffected_session_ids=["sess_2"],
        total_scheduled_sessions=2,
    )
    assert report.has_impact is True

    empty_report = ImpactReport(
        disruption=event,
        directly_affected_session_ids=[],
        directly_affected_assignments=[],
        unaffected_session_ids=["sess_1", "sess_2"],
        total_scheduled_sessions=2,
    )
    assert empty_report.has_impact is False


def test_recovery_result_properties():
    event = DisruptionEvent(
        id="d1",
        resource_type=ResourceType.ROOM,
        resource_id="r1",
        slot_ids={"s1"},
    )
    orig = ScheduledAssignment(session_id="s1", teacher_id="t1", room_id="r1", slot_id="s1")
    new_a = ScheduledAssignment(session_id="s1", teacher_id="t1", room_id="r2", slot_id="s1")
    change = AssignmentChange(
        session_id="s1",
        original_assignment=orig,
        new_assignment=new_a,
        changed_room=True,
        reason="Moved to room r2",
    )
    result = DisruptionRecoveryResult(
        disruption=event,
        status=SolverStatus.OPTIMAL,
        original_assignments=[orig],
        recovered_assignments=[new_a],
        directly_affected_session_ids=["s1"],
        moved_session_ids=["s1"],
        unaffected_session_ids=[],
        changes=[change],
        total_penalty=1,
        validation_passed=True,
    )
    assert result.is_success is True
    assert result.total_changes == 1
