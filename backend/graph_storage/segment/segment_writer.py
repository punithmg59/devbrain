"""
SegmentWriter implementation delegating physical writes to SegmentRepository.
"""

from graph_storage.exceptions import GraphStorageError
from graph_storage.model import SegmentDescriptor, SegmentId
from graph_storage.segment.segment_repository import SegmentRepository
from graph_storage.segment.segment_validator import SegmentValidator


class SegmentWriter:
    """Component responsible for validating and persisting segment data to repository."""

    def __init__(self, repository: SegmentRepository):
        self.repository = repository

    def validate_before_write(self, segment_id: SegmentId, data: bytes) -> None:
        """Run pre-write integrity and size validations."""
        SegmentValidator.validate_identifier(segment_id)
        SegmentValidator.validate_size(data)
        SegmentValidator.validate_structure(data)

    def persist_segment(self, segment_id: SegmentId, data: bytes) -> SegmentDescriptor:
        """Persist a new storage segment if it does not already exist."""
        self.validate_before_write(segment_id, data)
        if self.repository.exists(segment_id):
            raise GraphStorageError(f"Segment already exists: {segment_id.value}")
        return self.repository.save(segment_id, data)

    def overwrite_segment(self, segment_id: SegmentId, data: bytes) -> SegmentDescriptor:
        """Overwrite an existing or create a new storage segment."""
        self.validate_before_write(segment_id, data)
        return self.repository.save(segment_id, data)
