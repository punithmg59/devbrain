"""
PlacementStrategy abstract interface and DefaultPlacementStrategy implementation.
"""

from abc import ABC, abstractmethod
from typing import List

from graph_storage.exceptions import GraphStorageError
from graph_storage.model import PartitionId, SegmentId
from graph_storage.partitioning.partition_descriptor import PartitionDescriptor


class PlacementStrategy(ABC):
    """Abstract strategy interface for segment placement across storage partitions."""

    @abstractmethod
    def select_partition(self, segment_id: SegmentId, partitions: List[PartitionDescriptor]) -> PartitionId:
        """Select an optimal partition for segment placement."""
        ...

    @abstractmethod
    def validate_placement(self, segment_id: SegmentId, partition_id: PartitionId) -> bool:
        """Validate whether a segment placement satisfies strategy rules."""
        ...


class DefaultPlacementStrategy(PlacementStrategy):
    """Default strategy selecting partition with lowest utilization ratio."""

    def select_partition(self, segment_id: SegmentId, partitions: List[PartitionDescriptor]) -> PartitionId:
        if not partitions:
            raise GraphStorageError("No partitions available for placement selection")

        active_partitions = [p for p in partitions if p.status == "ACTIVE"]
        if not active_partitions:
            active_partitions = partitions

        # Pick partition with lowest utilization ratio (current_size / capacity)
        best_partition = min(
            active_partitions,
            key=lambda p: (p.current_size_bytes / p.capacity_bytes) if p.capacity_bytes > 0 else 1.0,
        )
        return best_partition.partition_id

    def validate_placement(self, segment_id: SegmentId, partition_id: PartitionId) -> bool:
        return bool(segment_id and segment_id.value and partition_id and partition_id.value)
