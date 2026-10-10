"""Unit and integration tests for solver-verified alternative generation."""

import pytest
from gecompose.alternatives import AlternativeGenerator, generate_alternatives
from gecompose.models import (
    ConstraintType,
    RelaxationPolicy,
    Room,
    SchedulingProblem,
    Session,
    SolverStatus,
    Teacher,
    TimeSlot,
)


class TestAlternativeGeneration:
    def test_slot_relaxation_alternative_found(self):
        """When teacher is unavailable at pinned slot, alternative generator moves session to an available slot."""
        problem = SchedulingProblem(
            teachers=[
                Teacher(
                    id="t_rao",
                    name="Prof. Rao",
                    qualifications={"Databases"},
                    unavailable_slots={"mon_09"},
                )
            ],
            rooms=[Room(id="r1", name="Lab 1", capacity=40)],
            slots=[
                TimeSlot(id="mon_09", day="Monday", start_time="09:00", end_time="10:00"),
                TimeSlot(id="mon_10", day="Monday", start_time="10:00", end_time="11:00"),
            ],
            sessions=[
                Session(
                    id="sess_db",
                    subject="Databases",
                    pinned_teacher_id="t_rao",
                    pinned_slot_id="mon_09",
                )
            ],
        )

        result = generate_alternatives(problem)
        assert result.status == SolverStatus.FEASIBLE
        assert result.original_status == SolverStatus.INFEASIBLE
        assert len(result.alternatives) >= 1

        alt = result.alternatives[0]
        assert alt.validation_passed is True
        assert len(alt.assignments) == 1
        assert alt.assignments[0].slot_id == "mon_10"
        assert alt.assignments[0].teacher_id == "t_rao"

        # Check relaxed requirement records
        assert len(alt.relaxed_requirements) == 1
        rel = alt.relaxed_requirements[0]
        assert rel.session_id == "sess_db"
        assert rel.constraint_type == ConstraintType.PINNED_SLOT
        assert rel.original_value == "mon_09"
        assert rel.relaxed_value == "mon_10"

    def test_teacher_swap_alternative_found(self):
        """When pinned teacher is busy, alternative generator swaps to another qualified teacher."""
        problem = SchedulingProblem(
            teachers=[
                Teacher(id="t_rao", name="Prof. Rao", qualifications={"Databases"}),
                Teacher(id="t_mehta", name="Prof. Mehta", qualifications={"Databases"}),
            ],
            rooms=[
                Room(id="r1", name="Lab 1", capacity=50),
                Room(id="r2", name="Lab 2", capacity=50),
            ],
            slots=[TimeSlot(id="mon_09", day="Monday", start_time="09:00", end_time="10:00")],
            sessions=[
                Session(
                    id="s1",
                    subject="Databases",
                    pinned_teacher_id="t_rao",
                    pinned_slot_id="mon_09",
                ),
                Session(
                    id="s2",
                    subject="Databases",
                    pinned_teacher_id="t_rao",  # Conflict: both want Rao at mon_09
                    pinned_slot_id="mon_09",
                ),
            ],
        )

        result = generate_alternatives(problem)
        assert result.status == SolverStatus.FEASIBLE
        assert len(result.alternatives) >= 1

        alt = result.alternatives[0]
        assert alt.validation_passed is True
        # Exactly one session should have teacher swapped to Mehta
        teacher_set = {a.teacher_id for a in alt.assignments}
        assert teacher_set == {"t_rao", "t_mehta"}

    def test_multiple_distinct_alternatives(self):
        """Generator returns multiple distinct alternatives without duplicates."""
        problem = SchedulingProblem(
            teachers=[
                Teacher(
                    id="t_rao",
                    name="Prof. Rao",
                    qualifications={"Databases"},
                    unavailable_slots={"mon_09"},
                )
            ],
            rooms=[Room(id="r1", name="Lab 1", capacity=50)],
            slots=[
                TimeSlot(id="mon_09", day="Monday", start_time="09:00", end_time="10:00"),
                TimeSlot(id="mon_10", day="Monday", start_time="10:00", end_time="11:00"),
                TimeSlot(id="tue_09", day="Tuesday", start_time="09:00", end_time="10:00"),
                TimeSlot(id="wed_09", day="Wednesday", start_time="09:00", end_time="10:00"),
            ],
            sessions=[
                Session(
                    id="sess_db",
                    subject="Databases",
                    pinned_teacher_id="t_rao",
                    pinned_slot_id="mon_09",
                )
            ],
        )

        policy = RelaxationPolicy(max_alternatives=3)
        result = generate_alternatives(problem, policy=policy)
        assert result.status == SolverStatus.FEASIBLE
        assert len(result.alternatives) == 3

        # All 3 alternatives must be distinct slots
        slots_used = [alt.assignments[0].slot_id for alt in result.alternatives]
        assert len(set(slots_used)) == 3
        assert "mon_09" not in slots_used

    def test_relaxation_policy_restrictions_honored(self):
        """When slot relaxation is disabled, generator does not relax slot pinning."""
        problem = SchedulingProblem(
            teachers=[
                Teacher(
                    id="t_rao",
                    name="Prof. Rao",
                    qualifications={"Databases"},
                    unavailable_slots={"mon_09"},
                )
            ],
            rooms=[Room(id="r1", name="Lab 1", capacity=50)],
            slots=[
                TimeSlot(id="mon_09", day="Monday", start_time="09:00", end_time="10:00"),
                TimeSlot(id="mon_10", day="Monday", start_time="10:00", end_time="11:00"),
            ],
            sessions=[
                Session(
                    id="sess_db",
                    subject="Databases",
                    pinned_teacher_id="t_rao",
                    pinned_slot_id="mon_09",
                )
            ],
        )

        # Disallow slot relaxation and teacher relaxation
        policy = RelaxationPolicy(allow_slot_relaxation=False, allow_teacher_relaxation=False)
        result = generate_alternatives(problem, policy=policy)
        assert result.status == SolverStatus.INFEASIBLE
        assert len(result.alternatives) == 0

    def test_non_negotiable_qualification_remains_enforced(self):
        """Alternatives never violate hard qualification requirements."""
        problem = SchedulingProblem(
            teachers=[
                Teacher(id="t1", name="Prof. Rao", qualifications={"Math"}),
                Teacher(id="t2", name="Prof. Mehta", qualifications={"Physics"}),
            ],
            rooms=[Room(id="r1", name="Room 1", capacity=50)],
            slots=[TimeSlot(id="s1", day="Monday", start_time="09:00", end_time="10:00")],
            sessions=[Session(id="sess_qc", subject="Quantum Computing")],  # Neither teacher has QC
        )

        result = generate_alternatives(problem)
        assert result.status == SolverStatus.INFEASIBLE
        assert len(result.alternatives) == 0
