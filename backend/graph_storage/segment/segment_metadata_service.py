"""
SegmentMetadataService handling metadata descriptors, statistics, and lookups.
"""

from typing import Dict, Optional

from graph_storage.model import SegmentDescriptor, SegmentId, SegmentMetadata
from graph_storage.segment.segment_reader import SegmentReader
from graph_storage.segment.segment_repository import SegmentRepository


class SegmentMetadataService:
    """Metadata service for segment statistics and descriptor inspection."""

    def __init__(self, repository: SegmentRepository, reader: SegmentReader):
        self.repository = repository
        self.reader = reader

    def metadata(self, segment_id: SegmentId) -> SegmentMetadata:
        """Retrieve segment metadata."""
        return self.reader.read_metadata(segment_id)

    def descriptor_lookup(self, segment_id: SegmentId) -> Optional[SegmentDescriptor]:
        """Look up segment descriptor by ID."""
        for desc in self.repository.list():
            if desc.metadata.segment_id == segment_id:
                return desc
        return None

    def statistics(self) -> Dict[str, int]:
        """Retrieve aggregate segment collection statistics."""
        descriptors = self.repository.list()
        total_bytes = sum(desc.metadata.size_bytes for desc in descriptors)
        return {
            "total_segments": len(descriptors),
            "total_bytes": total_bytes,
        }
