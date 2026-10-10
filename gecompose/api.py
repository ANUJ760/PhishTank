"""GeCompose public integration facade.

This module provides a thin, stateful facade (``GeComposeEngine``) and a set of
standalone helper functions that sit in front of the existing deterministic
OR-Tools CP-SAT scheduling engine.  All heavy lifting is delegated to the
lower-level modules (``solver``, ``diagnostics``, ``alternatives``,
``validator``).  This layer only:

- Accepts either a validated ``SchedulingProblem`` object *or* a plain dict and
  handles the Pydantic parsing boundary with a clean, structured error.
- Exposes a coherent public surface suitable for direct use from Python code,
  notebooks, or a future web layer.
- Converts result objects to plain JSON-serialisable dicts via Pydantic's
  ``.model_dump()``.
- Provides a ``to_timetable_grid`` utility that rearranges flat assignments into
  a 2-D view keyed by ``(day, slot_id)``.

Nothing in this module re-implements constraint solving, conflict diagnosis, or
alternative generation — those capabilities live in ``solver.py``,
``diagnostics.py``, and ``alternatives.py`` respectively.
"""

from __future__ import annotations

from typing import Any, Union

import pydantic

from gecompose.alternatives import generate_alternatives
from gecompose.diagnostics import diagnose_conflicts
from gecompose.exceptions import GeComposeError, SolverError, ValidationError
from gecompose.models import (
    AlternativeSearchResult,
    ConflictDiagnosis,
    RelaxationPolicy,
    ScheduledAssignment,
    ScheduleResult,
    SchedulingProblem,
    SolverStatus,
)
from gecompose.solver import CPSATScheduler, solve_schedule
from gecompose.validator import verify_schedule

# Public surface of this module.
__all__ = [
    "GeComposeEngine",
    "parse_problem",
    "schedule",
    "diagnose",
    "find_alternatives",
    "to_timetable_grid",
    "serialize_result",
]

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _coerce_problem(
    problem: Union[SchedulingProblem, dict[str, Any]],
) -> SchedulingProblem:
    """Return a validated ``SchedulingProblem``, accepting dicts as input.

    Args:
        problem: Either an already-validated ``SchedulingProblem`` instance or a
            plain dictionary that will be parsed with Pydantic.

    Returns:
        A validated ``SchedulingProblem`` instance.

    Raises:
        ValidationError: If the dictionary cannot be parsed or fails validation.
        TypeError: If *problem* is neither a ``SchedulingProblem`` nor a dict.
    """
    if isinstance(problem, SchedulingProblem):
        return problem
    if isinstance(problem, dict):
        try:
            return SchedulingProblem.model_validate(problem)
        except pydantic.ValidationError as exc:
            raise ValidationError(
                f"Invalid scheduling problem input: {exc}"
            ) from exc
    raise TypeError(
        f"Expected SchedulingProblem or dict, got {type(problem).__name__!r}"
    )


# ---------------------------------------------------------------------------
# Standalone functions
# ---------------------------------------------------------------------------

def parse_problem(
    data: Union[SchedulingProblem, dict[str, Any]],
) -> SchedulingProblem:
    """Parse and validate a scheduling problem from a dict or return as-is.

    Convenience wrapper around Pydantic validation.  Use this when you want to
    validate input before passing it to any engine method.

    Args:
        data: A plain dict conforming to the ``SchedulingProblem`` schema, or an
            already-constructed ``SchedulingProblem`` instance.

    Returns:
        A validated ``SchedulingProblem``.

    Raises:
        ValidationError: If *data* is a dict that fails schema validation.
        TypeError: If *data* is neither a dict nor a ``SchedulingProblem``.
    """
    return _coerce_problem(data)


def schedule(
    problem: Union[SchedulingProblem, dict[str, Any]],
    *,
    time_limit_seconds: float = 10.0,
    num_workers: int = 1,
) -> ScheduleResult:
    """Solve a scheduling problem and return a verified result.

    Accepts a ``SchedulingProblem`` object or a plain dict.  Returns a
    ``ScheduleResult`` whose ``is_success`` property is ``True`` only when a
    solution was found *and* independent constraint verification passed.

    Args:
        problem: Validated ``SchedulingProblem`` or equivalent dict.
        time_limit_seconds: Maximum wall time for the solver (seconds).
        num_workers: Number of parallel CP-SAT search workers.

    Returns:
        ``ScheduleResult`` with status, assignments, and verification metadata.

    Raises:
        ValidationError: If *problem* is a dict that fails validation.
        SolverError: If an unexpected internal error occurs in the solver.
    """
    validated = _coerce_problem(problem)
    try:
        return solve_schedule(
            validated,
            time_limit_seconds=time_limit_seconds,
            num_workers=num_workers,
        )
    except GeComposeError:
        raise
    except Exception as exc:  # pragma: no cover — unexpected solver internals
        raise SolverError(f"Unexpected solver error: {exc}") from exc


def diagnose(
    problem: Union[SchedulingProblem, dict[str, Any]],
    *,
    timeout_seconds: float = 5.0,
    minimize_core: bool = True,
) -> ConflictDiagnosis:
    """Diagnose why a scheduling problem is infeasible.

    Delegates to ``diagnose_conflicts()``.  Accepts dicts for convenience at the
    API boundary.

    Args:
        problem: ``SchedulingProblem`` or equivalent dict.
        timeout_seconds: Time budget for the diagnostic solver (seconds).
        minimize_core: Whether to attempt Minimal Unsatisfiable Subset (MUS)
            reduction.  When ``True``, the returned core is smaller but
            diagnosis takes longer.

    Returns:
        ``ConflictDiagnosis`` describing the conflict core and participating
        entities.

    Raises:
        ValidationError: If *problem* is a dict that fails validation.
        SolverError: If an unexpected internal error occurs during diagnosis.
    """
    validated = _coerce_problem(problem)
    try:
        return diagnose_conflicts(
            validated,
            timeout_seconds=timeout_seconds,
            minimize_core=minimize_core,
        )
    except GeComposeError:
        raise
    except Exception as exc:  # pragma: no cover — unexpected solver internals
        raise SolverError(f"Unexpected error during diagnosis: {exc}") from exc


def find_alternatives(
    problem: Union[SchedulingProblem, dict[str, Any]],
    *,
    policy: RelaxationPolicy | None = None,
) -> AlternativeSearchResult:
    """Generate solver-verified alternative schedules via constraint relaxation.

    Delegates to ``generate_alternatives()``.  Accepts dicts for convenience at
    the API boundary.

    Args:
        problem: ``SchedulingProblem`` or equivalent dict.
        policy: ``RelaxationPolicy`` controlling which constraints may be softened
            and how many alternatives to search for.  Defaults to the engine's
            built-in policy when ``None``.

    Returns:
        ``AlternativeSearchResult`` containing verified alternatives and search
        metadata.

    Raises:
        ValidationError: If *problem* is a dict that fails validation.
        SolverError: If an unexpected internal error occurs.
    """
    validated = _coerce_problem(problem)
    try:
        return generate_alternatives(validated, policy=policy)
    except GeComposeError:
        raise
    except Exception as exc:  # pragma: no cover — unexpected solver internals
        raise SolverError(
            f"Unexpected error during alternative search: {exc}"
        ) from exc


def to_timetable_grid(
    result: ScheduleResult,
    problem: SchedulingProblem,
) -> dict[tuple[str, str], list[ScheduledAssignment]]:
    """Convert a flat assignment list into a 2-D timetable grid.

    The grid is keyed by ``(day, slot_id)`` tuples and maps to the list of
    ``ScheduledAssignment`` objects that fall in that cell.  Slots with no
    assignments produce no entry in the returned dict.

    Args:
        result: A ``ScheduleResult`` returned by :func:`schedule` or any solver
            method.  Only *successful* results (``result.is_success == True``)
            are guaranteed to have a non-empty assignment list; the function
            still processes partial or feasible-only results.
        problem: The original ``SchedulingProblem`` used to produce *result*,
            needed to resolve slot metadata (``day`` field).

    Returns:
        ``dict`` mapping ``(day, slot_id)`` → ``list[ScheduledAssignment]``.
        The day string is taken from the corresponding ``TimeSlot.day`` field.

    Raises:
        ValueError: If an assignment references a slot ID that does not exist in
            *problem*.
    """
    slot_by_id = {s.id: s for s in problem.slots}
    grid: dict[tuple[str, str], list[ScheduledAssignment]] = {}

    for assignment in result.assignments:
        slot = slot_by_id.get(assignment.slot_id)
        if slot is None:
            raise ValueError(
                f"Assignment references unknown slot_id {assignment.slot_id!r}. "
                "Ensure the result was produced from the same problem."
            )
        key = (slot.day, slot.id)
        grid.setdefault(key, []).append(assignment)

    return grid


def serialize_result(
    result: Union[ScheduleResult, ConflictDiagnosis, AlternativeSearchResult],
) -> dict[str, Any]:
    """Serialize a result object to a JSON-serialisable plain dict.

    Calls Pydantic's ``.model_dump()`` with ``mode='json'`` so that enum values
    become strings, sets become lists, and all types are JSON-native.

    Args:
        result: Any of ``ScheduleResult``, ``ConflictDiagnosis``, or
            ``AlternativeSearchResult``.

    Returns:
        A plain ``dict`` that can be passed directly to ``json.dumps()``.

    Raises:
        TypeError: If *result* is not one of the recognised result types.
    """
    if not isinstance(
        result, (ScheduleResult, ConflictDiagnosis, AlternativeSearchResult)
    ):
        raise TypeError(
            f"Expected ScheduleResult, ConflictDiagnosis, or "
            f"AlternativeSearchResult, got {type(result).__name__!r}"
        )
    return result.model_dump(mode="json")


# ---------------------------------------------------------------------------
# Stateful facade class
# ---------------------------------------------------------------------------


class GeComposeEngine:
    """Stateful integration facade for the GeCompose deterministic scheduler.

    Wraps ``CPSATScheduler`` and the diagnostic/alternative modules behind a
    single object whose configuration is set once at construction time.  All
    methods accept either validated ``SchedulingProblem`` instances or plain
    dicts, converting at the API boundary and raising :class:`ValidationError`
    on invalid input.

    Example::

        from gecompose.api import GeComposeEngine
        from gecompose.models import SchedulingProblem, RelaxationPolicy

        engine = GeComposeEngine(time_limit_seconds=15.0)
        result = engine.schedule(problem)
        if not result.is_success:
            diagnosis = engine.diagnose(problem)
            alternatives = engine.find_alternatives(problem)
        grid = engine.to_timetable_grid(result, problem)
        data = engine.serialize_result(result)
    """

    def __init__(
        self,
        *,
        time_limit_seconds: float = 10.0,
        num_workers: int = 1,
        log_search_progress: bool = False,
        diagnosis_timeout_seconds: float = 5.0,
        minimize_conflict_core: bool = True,
    ) -> None:
        """Initialise the engine with solver and diagnostic configuration.

        Args:
            time_limit_seconds: Maximum wall time for the CP-SAT solver.
            num_workers: Number of parallel search workers.
            log_search_progress: Forward CP-SAT search logs to stdout.
            diagnosis_timeout_seconds: Time budget for conflict diagnosis.
            minimize_conflict_core: Attempt MUS reduction during diagnosis.
        """
        self._scheduler = CPSATScheduler(
            time_limit_seconds=time_limit_seconds,
            num_workers=num_workers,
            log_search_progress=log_search_progress,
        )
        self._diagnosis_timeout = diagnosis_timeout_seconds
        self._minimize_core = minimize_conflict_core

    # ------------------------------------------------------------------
    # Core scheduling
    # ------------------------------------------------------------------

    def schedule(
        self,
        problem: Union[SchedulingProblem, dict[str, Any]],
    ) -> ScheduleResult:
        """Solve *problem* and return a verified ``ScheduleResult``.

        Args:
            problem: ``SchedulingProblem`` or equivalent dict.

        Returns:
            ``ScheduleResult``.  ``result.is_success`` is ``True`` only when a
            solution was found *and* independent verification passed.

        Raises:
            ValidationError: If dict input fails validation.
            SolverError: If an unexpected internal error occurs.
        """
        validated = _coerce_problem(problem)
        try:
            return self._scheduler.solve(validated)
        except GeComposeError:
            raise
        except Exception as exc:  # pragma: no cover
            raise SolverError(f"Unexpected solver error: {exc}") from exc

    # ------------------------------------------------------------------
    # Conflict diagnosis
    # ------------------------------------------------------------------

    def diagnose(
        self,
        problem: Union[SchedulingProblem, dict[str, Any]],
        *,
        timeout_seconds: float | None = None,
        minimize_core: bool | None = None,
    ) -> ConflictDiagnosis:
        """Diagnose infeasibility in *problem*.

        Uses the engine's configured defaults for ``timeout_seconds`` and
        ``minimize_core`` unless overridden per call.

        Args:
            problem: ``SchedulingProblem`` or equivalent dict.
            timeout_seconds: Override the engine's diagnosis timeout.
            minimize_core: Override the engine's MUS-reduction flag.

        Returns:
            ``ConflictDiagnosis``.

        Raises:
            ValidationError: If dict input fails validation.
            SolverError: If an unexpected internal error occurs.
        """
        validated = _coerce_problem(problem)
        t = timeout_seconds if timeout_seconds is not None else self._diagnosis_timeout
        m = minimize_core if minimize_core is not None else self._minimize_core
        try:
            return diagnose_conflicts(validated, timeout_seconds=t, minimize_core=m)
        except GeComposeError:
            raise
        except Exception as exc:  # pragma: no cover
            raise SolverError(f"Unexpected error during diagnosis: {exc}") from exc

    # ------------------------------------------------------------------
    # Alternative generation
    # ------------------------------------------------------------------

    def find_alternatives(
        self,
        problem: Union[SchedulingProblem, dict[str, Any]],
        *,
        policy: RelaxationPolicy | None = None,
    ) -> AlternativeSearchResult:
        """Search for verified alternative schedules via constraint relaxation.

        Args:
            problem: ``SchedulingProblem`` or equivalent dict.
            policy: Relaxation policy.  Uses the module default when ``None``.

        Returns:
            ``AlternativeSearchResult``.

        Raises:
            ValidationError: If dict input fails validation.
            SolverError: If an unexpected internal error occurs.
        """
        validated = _coerce_problem(problem)
        try:
            return generate_alternatives(validated, policy=policy)
        except GeComposeError:
            raise
        except Exception as exc:  # pragma: no cover
            raise SolverError(
                f"Unexpected error during alternative search: {exc}"
            ) from exc

    # ------------------------------------------------------------------
    # Utilities
    # ------------------------------------------------------------------

    def to_timetable_grid(
        self,
        result: ScheduleResult,
        problem: Union[SchedulingProblem, dict[str, Any]],
    ) -> dict[tuple[str, str], list[ScheduledAssignment]]:
        """Convert a flat assignment list to a ``(day, slot_id)`` grid.

        See module-level :func:`to_timetable_grid` for full documentation.

        Args:
            result: ``ScheduleResult`` produced by :meth:`schedule`.
            problem: The ``SchedulingProblem`` (or dict) used to produce *result*.

        Returns:
            ``dict`` mapping ``(day, slot_id)`` → ``list[ScheduledAssignment]``.

        Raises:
            ValidationError: If *problem* dict fails validation.
            ValueError: If an assignment references an unknown slot ID.
        """
        validated = _coerce_problem(problem)
        return to_timetable_grid(result, validated)

    def serialize_result(
        self,
        result: Union[ScheduleResult, ConflictDiagnosis, AlternativeSearchResult],
    ) -> dict[str, Any]:
        """Serialize a result object to a JSON-serialisable plain dict.

        See module-level :func:`serialize_result` for full documentation.

        Args:
            result: ``ScheduleResult``, ``ConflictDiagnosis``, or
                ``AlternativeSearchResult``.

        Returns:
            Plain ``dict`` safe for ``json.dumps()``.
        """
        return serialize_result(result)

    def verify(
        self,
        problem: Union[SchedulingProblem, dict[str, Any]],
        assignments: list[ScheduledAssignment],
    ) -> tuple[bool, list[str]]:
        """Run the independent constraint checker against a set of assignments.

        Args:
            problem: ``SchedulingProblem`` (or dict) defining the constraints.
            assignments: List of ``ScheduledAssignment`` objects to verify.

        Returns:
            ``(passed, violations)`` where *passed* is ``True`` when no
            violations were found and *violations* is the list of violation
            messages.

        Raises:
            ValidationError: If dict input fails validation.
        """
        validated = _coerce_problem(problem)
        return verify_schedule(validated, assignments)
