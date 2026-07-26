"""
SegmentLifecycleManager implementation for managing segment state transitions.
"""

import threading
from typing import Dict, Optional

from graph_storage.exceptions import GraphStorageError, SegmentNotFoundError
from graph_storage.model import SegmentDescriptor, SegmentId
from graph_storage.segment.segment_manager import SegmentManager
from graph_storage.segment.segment_state_machine import SegmentState, SegmentStateMachine


class SegmentLifecycleManager:
    """Manager handling segment creation, replacement, archiving, recovery, and deletion transitions."""

    def __init__(self, segment_manager: SegmentManager):
        self.manager = segment_manager
        self.state_machine = segment_manager.state_machine
        self._archive_store: Dict[SegmentId, bytes] = {}
        self._lock = threading.RLock()

    def create(self, segment_id: SegmentId, data: bytes) -> SegmentDescriptor:
        """Create a segment and set state to ACTIVE."""
        with self._lock:
            descriptor = self.manager.create_segment(segment_id, data)
            return descriptor

    def replace(self, segment_id: SegmentId, new_data: bytes) -> SegmentDescriptor:
        """Replace an existing segment's payload and record state transition."""
        with self._lock:
            if not self.manager.segment_exists(segment_id):
                raise SegmentNotFoundError(f"Cannot replace non-existent segment: {segment_id.value}")
            descriptor = self.manager.command_service.replace(segment_id, new_data)
            return descriptor

    def archive(self, segment_id: SegmentId) -> bool:
        """Archive an active segment."""
        with self._lock:
            if not self.manager.segment_exists(segment_id):
                raise SegmentNotFoundError(f"Cannot archive non-existent segment: {segment_id.value}")
            data = self.manager.load_segment(segment_id)
            self._archive_store[segment_id] = data
            self.manager.repository.delete(segment_id)
            self.state_machine.transition(segment_id, SegmentState.ARCHIVED)
            return True

    def recover(self, segment_id: SegmentId) -> bool:
        """Recover an archived segment back to ACTIVE state."""
        with self._lock:
            if segment_id not in self._archive_store:
                raise GraphStorageError(f"No archive payload found for segment: {segment_id.value}")
            self.state_machine.transition(segment_id, SegmentState.RECOVERING)
            data = self._archive_store.pop(segment_id)
            self.manager.writer.overwrite_segment(segment_id, data)
            self.state_machine.transition(segment_id, SegmentState.ACTIVE)
            return True

    def delete(self, segment_id: SegmentId) -> bool:
        """Delete a segment and set state to DELETED."""
        with self._lock:
            self._archive_store.pop(segment_id, None)
            deleted = self.manager.delete_segment(segment_id)
            return deleted

    def get_state(self, segment_id: SegmentId) -> SegmentState:
        """Get the current lifecycle state of a segment."""
        with self._lock:
            return self.state_machine.get_state(segment_id)
