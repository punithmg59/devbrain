"""
PartitioningStrategy abstract interface.
"""

from abc import ABC, abstractmethod
from graph_storage.model import SegmentId, PartitionId, SegmentMetadata


class PartitioningStrategy(ABC):
    """Abstract interface for artifact storage partitioning policies."""

    @abstractmethod
    def choose_partition(self, segment_id: SegmentId, metadata: SegmentMetadata) -> PartitionId:
        """Select a partition location for a storage segment."""
        ...

    @abstractmethod
    def partition_key(self, segment_id: SegmentId) -> PartitionId:
        """Generate the partition identifier for a given segment ID."""
        ...

    @abstractmethod
    def validate_partition(self, partition_id: PartitionId) -> bool:
        """Validate whether a partition identifier satisfies strategy requirements."""
        ...
