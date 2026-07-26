"""
SegmentQueryService handling read, existence, and listing queries.
"""

from typing import List

from graph_storage.model import SegmentDescriptor, SegmentId
from graph_storage.segment.segment_reader import SegmentReader
from graph_storage.segment.segment_repository import SegmentRepository


class SegmentQueryService:
    """Query service for segment reads."""

    def __init__(self, repository: SegmentRepository, reader: SegmentReader):
        self.repository = repository
        self.reader = reader

    def load(self, segment_id: SegmentId) -> bytes:
        """Load segment data payload."""
        return self.reader.read_segment(segment_id)

    def exists(self, segment_id: SegmentId) -> bool:
        """Check segment existence."""
        return self.repository.exists(segment_id)

    def list(self) -> List[SegmentDescriptor]:
        """List all segment descriptors."""
        return self.repository.list()
