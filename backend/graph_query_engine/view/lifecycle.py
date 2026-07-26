"""
GraphView Lifecycle States and State Machine Definitions.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import StrEnum
from typing import Optional


class GraphViewLifecycleState(StrEnum):
    """
    Lifecycle operational states for a GraphView instance.
    """
    CREATED = "CREATED"
    BUILDING = "BUILDING"
    VALIDATING = "VALIDATING"
    READY = "READY"
    FAILED = "FAILED"
    DISPOSED = "DISPOSED"


@dataclass(frozen=True)
class GraphViewLifecycleStatus:
    """
    Immutable status container tracking GraphView lifecycle state transitions.
    """
    state: GraphViewLifecycleState
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    error: Optional[str] = None


class GraphViewLifecycle:
    """
    State machine helper for managing GraphView lifecycle state transitions.
    """

    def __init__(self) -> None:
        self._state: GraphViewLifecycleState = GraphViewLifecycleState.CREATED
        self._history: list[GraphViewLifecycleStatus] = [
            GraphViewLifecycleStatus(state=GraphViewLifecycleState.CREATED)
        ]

    @property
    def current_state(self) -> GraphViewLifecycleState:
        """Returns the active lifecycle state."""
        return self._state

    def transition_to(self, new_state: GraphViewLifecycleState, error: Optional[str] = None) -> None:
        """
        Transitions state machine to new_state and records history log.
        """
        self._state = new_state
        self._history.append(GraphViewLifecycleStatus(state=new_state, error=error))

    def get_history(self) -> tuple[GraphViewLifecycleStatus, ...]:
        """Returns immutable tuple of state transition history."""
        return tuple(self._history)


__all__ = [
    "GraphViewLifecycleState",
    "GraphViewLifecycleStatus",
    "GraphViewLifecycle",
]
