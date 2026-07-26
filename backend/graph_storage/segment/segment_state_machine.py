"""
SegmentStateMachine implementation enforcing formal state transition rules.
"""

from enum import Enum, auto
from typing import Dict, Set

from graph_storage.exceptions import GraphStorageError
from graph_storage.model import SegmentId


class SegmentState(Enum):
    """Formal lifecycle states of a storage segment."""
    CREATED = auto()
    ACTIVE = auto()
    ARCHIVED = auto()
    REPLACED = auto()
    DELETED = auto()
    CORRUPTED = auto()
    MIGRATING = auto()
    COMPACTING = auto()
    RECOVERING = auto()


class SegmentStateMachine:
    """State machine enforcing valid segment state transitions."""

    _ALLOWED_TRANSITIONS: Dict[SegmentState, Set[SegmentState]] = {
        SegmentState.CREATED: {SegmentState.ACTIVE, SegmentState.DELETED, SegmentState.CORRUPTED},
        SegmentState.ACTIVE: {
            SegmentState.REPLACED,
            SegmentState.ARCHIVED,
            SegmentState.DELETED,
            SegmentState.CORRUPTED,
            SegmentState.MIGRATING,
            SegmentState.COMPACTING,
        },
        SegmentState.REPLACED: {SegmentState.ARCHIVED, SegmentState.DELETED, SegmentState.CORRUPTED},
        SegmentState.ARCHIVED: {SegmentState.RECOVERING, SegmentState.DELETED, SegmentState.CORRUPTED},
        SegmentState.RECOVERING: {SegmentState.ACTIVE, SegmentState.CORRUPTED},
        SegmentState.MIGRATING: {SegmentState.ACTIVE, SegmentState.CORRUPTED},
        SegmentState.COMPACTING: {SegmentState.ACTIVE, SegmentState.CORRUPTED},
        SegmentState.CORRUPTED: {SegmentState.DELETED, SegmentState.RECOVERING},
        SegmentState.DELETED: set(),
    }

    def __init__(self):
        self._current_states: Dict[SegmentId, SegmentState] = {}

    def get_state(self, segment_id: SegmentId) -> SegmentState:
        """Retrieve current lifecycle state for a segment (defaults to CREATED)."""
        return self._current_states.get(segment_id, SegmentState.CREATED)

    def transition(self, segment_id: SegmentId, target_state: SegmentState) -> SegmentState:
        """Transition a segment to a target state, rejecting illegal transitions."""
        current = self.get_state(segment_id)
        allowed = self._ALLOWED_TRANSITIONS.get(current, set())
        if target_state not in allowed:
            raise GraphStorageError(
                f"Illegal state transition for segment '{segment_id.value}': {current.name} -> {target_state.name}"
            )
        self._current_states[segment_id] = target_state
        return target_state
