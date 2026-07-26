"""
PartitionIndex query service for fast partition and segment placement lookup.
"""

from typing import Dict, List, Optional, Set
from graph_storage.model import PartitionId, SegmentId
from graph_storage.partitioning.partition_descriptor import PartitionDescriptor


class PartitionIndex:
    """In-memory indexing query service for partition descriptors and segment mappings."""

    def __init__(self):
        self._partitions: Dict[PartitionId, PartitionDescriptor] = {}
        self._segment_to_partition: Dict[SegmentId, PartitionId] = {}
        self._partition_to_segments: Dict[PartitionId, Set[SegmentId]] = {}

    def index_partition(self, descriptor: PartitionDescriptor) -> None:
        """Index a partition descriptor."""
        pid = descriptor.partition_id
        self._partitions[pid] = descriptor
        if pid not in self._partition_to_segments:
            self._partition_to_segments[pid] = set()

    def map_segment(self, segment_id: SegmentId, partition_id: PartitionId) -> None:
        """Map a segment to a partition."""
        self._segment_to_partition[segment_id] = partition_id
        if partition_id not in self._partition_to_segments:
            self._partition_to_segments[partition_id] = set()
        self._partition_to_segments[partition_id].add(segment_id)

    def find_partition(self, partition_id: PartitionId) -> Optional[PartitionDescriptor]:
        """Look up partition descriptor by ID."""
        return self._partitions.get(partition_id)

    def find_segment(self, segment_id: SegmentId) -> Optional[PartitionId]:
        """Look up partition ID containing the given segment."""
        return self._segment_to_partition.get(segment_id)

    def reverse_lookup(self, partition_id: PartitionId) -> Set[SegmentId]:
        """Get set of all segments mapped to a partition."""
        return self._partition_to_segments.get(partition_id, set())

    def partition_usage(self, partition_id: PartitionId) -> int:
        """Get count of segments mapped to a partition."""
        return len(self.reverse_lookup(partition_id))

    def statistics(self) -> Dict[str, int]:
        """Get aggregate index statistics."""
        return {
            "total_partitions": len(self._partitions),
            "total_mapped_segments": len(self._segment_to_partition),
        }
