"""
PartitionPlanner abstract interface and SimpleCapacityPlanner implementation.
"""

from abc import ABC, abstractmethod
from typing import List

from graph_storage.exceptions import GraphStorageError
from graph_storage.model import PartitionId, SegmentId
from graph_storage.partitioning.partition_descriptor import PartitionDescriptor
from graph_storage.partitioning.partition_policy import PartitionPolicy


class PartitionPlanner(ABC):
    """Abstract interface for planning segment partition assignments."""

    @abstractmethod
    def plan_placement(
        self, segment_id: SegmentId, data_size: int, partitions: List[PartitionDescriptor]
    ) -> PartitionId:
        """Plan partition assignment for a new segment of given data size."""
        ...


class SimpleCapacityPlanner(PartitionPlanner):
    """Planner checking partition capacity and policy constraints."""

    def __init__(self, policy: PartitionPolicy = PartitionPolicy()):
        self.policy = policy

    def plan_placement(
        self, segment_id: SegmentId, data_size: int, partitions: List[PartitionDescriptor]
    ) -> PartitionId:
        if not partitions:
            raise GraphStorageError("No partitions registered in capacity planner")

        available_partitions = []
        for p in partitions:
            if p.status != "ACTIVE":
                continue
            new_size = p.current_size_bytes + data_size
            max_allowed = min(p.capacity_bytes, self.policy.maximum_partition_size_bytes)
            if new_size <= max_allowed:
                available_partitions.append((p, new_size / max_allowed if max_allowed > 0 else 1.0))

        if not available_partitions:
            raise GraphStorageError("All active partitions have exceeded capacity limits for placement")

        # Pick partition that will remain least utilized after insertion
        best = min(available_partitions, key=lambda x: x[1])
        return best[0].partition_id
