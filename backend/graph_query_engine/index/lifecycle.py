"""
Index Lifecycle States and State Machine.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import StrEnum
from typing import Optional


class IndexLifecycleState(StrEnum):
    """
    Lifecycle operational states for an index instance.
    """
    CREATED = "CREATED"
    BUILDING = "BUILDING"
    VALIDATING = "VALIDATING"
    READY = "READY"
    FAILED = "FAILED"
    DISPOSED = "DISPOSED"


@dataclass(frozen=True)
class IndexLifecycleStatus:
    """
    Immutable status container tracking index lifecycle state transitions.
    """
    state: IndexLifecycleState
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    error: Optional[str] = None


class IndexLifecycle:
    """
    State machine helper for managing index lifecycle state transitions.
    """

    def __init__(self) -> None:
        self._state: IndexLifecycleState = IndexLifecycleState.CREATED
        self._history: list[IndexLifecycleStatus] = [
            IndexLifecycleStatus(state=IndexLifecycleState.CREATED)
        ]

    @property
    def current_state(self) -> IndexLifecycleState:
        """Returns the active index lifecycle state."""
        return self._state

    def transition_to(self, new_state: IndexLifecycleState, error: Optional[str] = None) -> None:
        """Transitions state machine to new_state and records history."""
        self._state = new_state
        self._history.append(IndexLifecycleStatus(state=new_state, error=error))

    def get_history(self) -> tuple[IndexLifecycleStatus, ...]:
        """Returns immutable tuple of state transition history."""
        return tuple(self._history)


__all__ = [
    "IndexLifecycleState",
    "IndexLifecycleStatus",
    "IndexLifecycle",
]
