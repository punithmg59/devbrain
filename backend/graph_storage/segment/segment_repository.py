"""
SegmentRepository pattern implementation wrapping StorageBackend and StorageLayout.
"""

from typing import List, Optional

from graph_storage.backend.storage_backend import StorageBackend
from graph_storage.backend.storage_layout import StorageLayout
from graph_storage.model import SegmentDescriptor, SegmentId, SegmentMetadata
from graph_storage.segment.segment_metadata_factory import SegmentMetadataFactory


class SegmentRepository:
    """Repository abstraction insulating higher storage layers from raw StorageBackend calls."""

    def __init__(self, backend: StorageBackend, layout: Optional[StorageLayout] = None):
        self.backend = backend
        self.layout = layout

    def save(self, segment_id: SegmentId, data: bytes) -> SegmentDescriptor:
        """Save a segment payload into physical storage."""
        return self.backend.write_segment(segment_id, data)

    def load(self, segment_id: SegmentId) -> bytes:
        """Load raw segment bytes from physical storage."""
        return self.backend.read_segment(segment_id)

    def delete(self, segment_id: SegmentId) -> bool:
        """Delete a segment from physical storage."""
        return self.backend.delete_segment(segment_id)

    def exists(self, segment_id: SegmentId) -> bool:
        """Check if a segment exists in physical storage."""
        return self.backend.exists_segment(segment_id)

    def list(self) -> List[SegmentDescriptor]:
        """List all segment descriptors available in storage."""
        return self.backend.list_segments()

    def metadata(self, segment_id: SegmentId) -> SegmentMetadata:
        """Retrieve metadata descriptor for a segment."""
        data = self.load(segment_id)
        return SegmentMetadataFactory.create_metadata(segment_id, data)
