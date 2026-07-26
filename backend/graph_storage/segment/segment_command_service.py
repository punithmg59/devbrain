"""
SegmentCommandService handling write, replace, and delete operations with state machine tracking.
"""

from graph_storage.exceptions import GraphStorageError
from graph_storage.model import SegmentDescriptor, SegmentId
from graph_storage.segment.segment_repository import SegmentRepository
from graph_storage.segment.segment_state_machine import SegmentState, SegmentStateMachine
from graph_storage.segment.segment_writer import SegmentWriter


class SegmentCommandService:
    """Command service for segment mutations."""

    def __init__(
        self,
        repository: SegmentRepository,
        writer: SegmentWriter,
        state_machine: SegmentStateMachine,
    ):
        self.repository = repository
        self.writer = writer
        self.state_machine = state_machine

    def create(self, segment_id: SegmentId, data: bytes) -> SegmentDescriptor:
        """Create a segment and transition state to ACTIVE."""
        descriptor = self.writer.persist_segment(segment_id, data)
        self.state_machine.transition(segment_id, SegmentState.ACTIVE)
        return descriptor

    def replace(self, segment_id: SegmentId, new_data: bytes) -> SegmentDescriptor:
        """Replace a segment and transition state to REPLACED."""
        if not self.repository.exists(segment_id):
            raise GraphStorageError(f"Cannot replace non-existent segment: {segment_id.value}")
        descriptor = self.writer.overwrite_segment(segment_id, new_data)
        self.state_machine.transition(segment_id, SegmentState.REPLACED)
        return descriptor

    def delete(self, segment_id: SegmentId) -> bool:
        """Delete a segment and transition state to DELETED."""
        deleted = self.repository.delete(segment_id)
        if deleted:
            self.state_machine.transition(segment_id, SegmentState.DELETED)
        return deleted
