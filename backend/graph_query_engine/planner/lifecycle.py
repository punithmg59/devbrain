"""
PlannerLifecycle Manager for Managing State Transitions.
"""

import threading
from typing import Mapping
from graph_query_engine.errors import InvalidPlannerStateError
from graph_query_engine.planner.state import PlannerState


class PlannerLifecycle:
    """
    Thread-safe lifecycle manager responsible ONLY for planner state transitions.
    Contains no query planning logic.
    """

    VALID_TRANSITIONS: Mapping[PlannerState, tuple[PlannerState, ...]] = {
        PlannerState.CREATED: (PlannerState.INITIALIZED, PlannerState.FAILED, PlannerState.CANCELLED),
        PlannerState.INITIALIZED: (PlannerState.VALIDATING, PlannerState.FAILED, PlannerState.CANCELLED),
        PlannerState.VALIDATING: (PlannerState.PLANNING, PlannerState.FAILED, PlannerState.CANCELLED),
        PlannerState.PLANNING: (PlannerState.OPTIMIZING, PlannerState.BUILDING_PLAN, PlannerState.FAILED, PlannerState.CANCELLED, PlannerState.TIMEOUT),
        PlannerState.OPTIMIZING: (PlannerState.BUILDING_PLAN, PlannerState.FAILED, PlannerState.CANCELLED, PlannerState.TIMEOUT),
        PlannerState.BUILDING_PLAN: (PlannerState.COMPLETED, PlannerState.FAILED, PlannerState.CANCELLED, PlannerState.TIMEOUT),
        PlannerState.COMPLETED: (),
        PlannerState.FAILED: (),
        PlannerState.CANCELLED: (),
        PlannerState.TIMEOUT: (),
    }

    def __init__(self, initial_state: PlannerState = PlannerState.CREATED) -> None:
        self._lock = threading.RLock()
        self._state = initial_state

    @property
    def current_state(self) -> PlannerState:
        """Returns the current PlannerState."""
        with self._lock:
            return self._state

    def transition_to(self, new_state: PlannerState | str) -> None:
        """
        Transitions lifecycle to new_state.
        Raises InvalidPlannerStateError if transition is invalid or state is terminal.
        """
        target = PlannerState(str(new_state).upper()) if isinstance(new_state, str) else new_state
        with self._lock:
            if self._state.is_terminal:
                raise InvalidPlannerStateError(
                    f"Cannot transition from terminal state '{self._state.value}' to '{target.value}'."
                )

            valid_targets = self.VALID_TRANSITIONS.get(self._state, ())
            if target not in valid_targets:
                raise InvalidPlannerStateError(
                    f"Invalid state transition from '{self._state.value}' to '{target.value}'. Allowed: {[s.value for s in valid_targets]}."
                )

            self._state = target

    def is_terminal(self) -> bool:
        """Returns True if the current state is terminal."""
        with self._lock:
            return self._state.is_terminal


__all__ = ["PlannerLifecycle"]
