"""End-to-end integration and workflow tests for GeCompose API facade."""

from __future__ import annotations

import json
import pytest

from gecompose.api import (
    GeComposeEngine,
    diagnose,
    find_alternatives,
    parse_problem,
    schedule,
    serialize_result,
    to_timetable_grid,
)
from gecompose.exceptions import ValidationError
from gecompose.models import (
    ConstraintType,
    RelaxationPolicy,
    Room,
    Session,
    SolverStatus,
    Teacher,
    TimeSlot,
    SchedulingProblem,
)


def _build_simple_feasible_problem() -> SchedulingProblem:
    slots = [
        TimeSlot(id="s1", day="Monday", start_time="09:00", end_time="10:00"),
        TimeSlot(id="s2", day="Monday", start_time="10:00", end_time="11:00"),
    ]
    teachers = [
        Teacher(id="t1", name="Alice", qualifications={"Math"}),
        Teacher(id="t2", name="Bob", qualifications={"Physics"}),
    ]
    rooms = [
        Room(id="r1", name="Room 101", capacity=30),
        Room(id="r2", name="Room 102", capacity=40),
    ]
    sessions = [
        Session(id="sess1", title="Math 101", subject="Math", expected_students=25),
        Session(id="sess2", title="Physics 101", subject="Physics", expected_students=35),
    ]
    return SchedulingProblem(
        slots=slots, teachers=teachers, rooms=rooms, sessions=sessions
    )


def _build_simple_infeasible_problem() -> SchedulingProblem:
    # 2 sessions pinned to same teacher, same slot
    slots = [
        TimeSlot(id="s1", day="Monday", start_time="09:00", end_time="10:00"),
        TimeSlot(id="s2", day="Monday", start_time="10:00", end_time="11:00"),
    ]
    teachers = [
        Teacher(id="t1", name="Alice", qualifications={"Math"}),
    ]
    rooms = [
        Room(id="r1", name="Room 101", capacity=30),
        Room(id="r2", name="Room 102", capacity=30),
    ]
    sessions = [
        Session(
            id="sess1",
            title="Math 101",
            subject="Math",
            pinned_teacher_id="t1",
            pinned_slot_id="s1",
        ),
        Session(
            id="sess2",
            title="Math 102",
            subject="Math",
            pinned_teacher_id="t1",
            pinned_slot_id="s1",
        ),
    ]
    return SchedulingProblem(
        slots=slots, teachers=teachers, rooms=rooms, sessions=sessions
    )


class TestGeComposeEngineE2E:
    """Test the stateful GeComposeEngine and standalone functions."""

    def test_solve_feasible_problem_and_grid(self):
        engine = GeComposeEngine(time_limit_seconds=5.0)
        prob = _build_simple_feasible_problem()

        res = engine.schedule(prob)
        assert res.is_success is True
        assert res.status in (SolverStatus.OPTIMAL, SolverStatus.FEASIBLE)
        assert len(res.assignments) == 2
        assert res.validation_passed is True
        assert len(res.violations) == 0

        # Grid generation
        grid = engine.to_timetable_grid(res, prob)
        assert len(grid) >= 1
        all_grid_assignments = [a for sub in grid.values() for a in sub]
        assert len(all_grid_assignments) == 2

        # Verify method
        passed, violations = engine.verify(prob, res.assignments)
        assert passed is True
        assert len(violations) == 0

    def test_solve_from_dict_input(self):
        engine = GeComposeEngine()
        raw_dict = {
            "slots": [
                {"id": "slot1", "day": "Monday", "start_time": "09:00", "end_time": "10:00"}
            ],
            "teachers": [
                {"id": "t1", "name": "Prof", "qualifications": ["CS"]}
            ],
            "rooms": [
                {"id": "r1", "name": "Lab A", "capacity": 20}
            ],
            "sessions": [
                {"id": "c1", "title": "Intro CS", "subject": "CS", "expected_students": 15}
            ],
        }
        res = engine.schedule(raw_dict)
        assert res.is_success is True
        assert len(res.assignments) == 1
        assert res.assignments[0].session_id == "c1"

    def test_malformed_dict_raises_validation_error(self):
        engine = GeComposeEngine()
        malformed = {
            "slots": [
                # Invalid: end_time before start_time
                {"id": "s1", "day": "Monday", "start_time": "10:00", "end_time": "09:00"}
            ]
        }
        with pytest.raises(ValidationError) as excinfo:
            engine.schedule(malformed)
        assert "Invalid scheduling problem input" in str(excinfo.value)

        # Non-dict non-SchedulingProblem type
        with pytest.raises(TypeError):
            engine.schedule("not a dict or problem")  # type: ignore

    def test_parse_problem_helper(self):
        raw = {
            "slots": [{"id": "s1", "day": "Tue", "start_time": "10:00", "end_time": "11:00"}],
            "teachers": [{"id": "t1", "name": "A"}],
            "rooms": [{"id": "r1", "name": "R"}],
            "sessions": [{"id": "sess1"}],
        }
        parsed = parse_problem(raw)
        assert isinstance(parsed, SchedulingProblem)
        assert parsed.slots[0].id == "s1"

        # Idempotent when already a SchedulingProblem
        assert parse_problem(parsed) is parsed

    def test_infeasible_problem_diagnosis_and_alternatives_e2e(self):
        engine = GeComposeEngine()
        infeasible_prob = _build_simple_infeasible_problem()

        # Step 1: Solve should fail or return INFEASIBLE
        res = engine.schedule(infeasible_prob)
        assert res.status == SolverStatus.INFEASIBLE
        assert res.is_success is False
        assert len(res.assignments) == 0

        # Step 2: Diagnose infeasibility
        diag = engine.diagnose(infeasible_prob)
        assert diag.is_infeasible is True
        assert diag.has_core is True
        assert len(diag.conflicting_constraints) > 0
        assert "sess1" in diag.diagnosed_entities.get("sessions", []) or "sess2" in diag.diagnosed_entities.get("sessions", [])

        # Step 3: Find verified alternatives
        policy = RelaxationPolicy(allow_slot_relaxation=True, max_alternatives=2)
        alt_res = engine.find_alternatives(infeasible_prob, policy=policy)
        assert alt_res.status in (SolverStatus.OPTIMAL, SolverStatus.FEASIBLE)
        assert len(alt_res.alternatives) > 0
        best_alt = alt_res.alternatives[0]
        assert best_alt.validation_passed is True
        assert len(best_alt.relaxed_requirements) > 0

    def test_standalone_functions(self):
        prob = _build_simple_feasible_problem()
        res = schedule(prob)
        assert res.is_success is True

        grid = to_timetable_grid(res, prob)
        assert len(grid) >= 1

        infeasible_prob = _build_simple_infeasible_problem()
        diag = diagnose(infeasible_prob)
        assert diag.is_infeasible is True

        alt_res = find_alternatives(infeasible_prob)
        assert len(alt_res.alternatives) > 0

    def test_serialize_result_to_json(self):
        engine = GeComposeEngine()
        prob = _build_simple_feasible_problem()
        res = engine.schedule(prob)

        # Test schedule result serialization
        dumped = engine.serialize_result(res)
        assert isinstance(dumped, dict)
        assert dumped["status"] in ("OPTIMAL", "FEASIBLE")
        assert isinstance(dumped["assignments"], list)
        # Verify fully valid JSON
        serialized_str = json.dumps(dumped)
        assert isinstance(serialized_str, str)

        # Test diagnosis serialization
        infeasible_prob = _build_simple_infeasible_problem()
        diag = engine.diagnose(infeasible_prob)
        diag_dumped = serialize_result(diag)
        assert isinstance(diag_dumped, dict)
        assert diag_dumped["is_infeasible"] is True
        assert json.dumps(diag_dumped)

        # Test alternative search result serialization
        alts = engine.find_alternatives(infeasible_prob)
        alts_dumped = serialize_result(alts)
        assert isinstance(alts_dumped, dict)
        assert len(alts_dumped["alternatives"]) > 0
        assert json.dumps(alts_dumped)

        # Invalid type check
        with pytest.raises(TypeError):
            serialize_result("not a result")  # type: ignore

    def test_to_timetable_grid_invalid_slot_id(self):
        prob = _build_simple_feasible_problem()
        res = schedule(prob)
        # Create different problem with missing slots
        empty_problem = SchedulingProblem(slots=[], teachers=[], rooms=[], sessions=[])
        with pytest.raises(ValueError) as exc:
            to_timetable_grid(res, empty_problem)
        assert "Assignment references unknown slot_id" in str(exc.value)
