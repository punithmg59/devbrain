"""
TransactionState enum and TransactionStateMachine implementation.
"""

from enum import Enum
from typing import Dict, List, Set
from graph_storage.exceptions import GraphStorageError


class TransactionState(Enum):
    CREATED = "CREATED"
    ACTIVE = "ACTIVE"
    PREPARING = "PREPARING"
    COMMITTED = "COMMITTED"
    ROLLED_BACK = "ROLLED_BACK"
    ABORTED = "ABORTED"
    FAILED = "FAILED"


class TransactionStateMachine:
    """Deterministic state machine governing transaction state transitions."""

    _ALLOWED_TRANSITIONS: Dict[TransactionState, Set[TransactionState]] = {
        TransactionState.CREATED: {TransactionState.ACTIVE, TransactionState.ABORTED, TransactionState.FAILED},
        TransactionState.ACTIVE: {TransactionState.PREPARING, TransactionState.ROLLED_BACK, TransactionState.ABORTED, TransactionState.FAILED},
        TransactionState.PREPARING: {TransactionState.COMMITTED, TransactionState.ROLLED_BACK, TransactionState.ABORTED, TransactionState.FAILED},
        TransactionState.COMMITTED: set(),
        TransactionState.ROLLED_BACK: set(),
        TransactionState.ABORTED: set(),
        TransactionState.FAILED: set(),
    }

    def __init__(self, initial_state: TransactionState = TransactionState.CREATED):
        self._history: List[TransactionState] = [initial_state]

    @property
    def current_state(self) -> TransactionState:
        return self._history[-1]

    def transition(self, target: TransactionState) -> TransactionState:
        """Validate and apply state transition."""
        curr = self.current_state
        allowed = self._ALLOWED_TRANSITIONS.get(curr, set())
        if target not in allowed:
            raise GraphStorageError(f"Invalid transaction state transition from {curr.value} to {target.value}")
        self._history.append(target)
        return target

    def history(self) -> List[TransactionState]:
        """Return full transition history."""
        return list(self._history)
