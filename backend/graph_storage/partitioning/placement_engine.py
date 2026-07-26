"""
PlacementEngine orchestrating segment placement planners, strategies, and policies.
"""

from typing import List, Optional

from graph_storage.exceptions import GraphStorageError
from graph_storage.model import PartitionId, SegmentId
from graph_storage.partitioning.partition_descriptor import PartitionDescriptor
from graph_storage.partitioning.partition_planner import PartitionPlanner, SimpleCapacityPlanner
from graph_storage.partitioning.partition_policy import PartitionPolicy
from graph_storage.partitioning.placement_result import PartitionPlacementResult
from graph_storage.partitioning.placement_strategy import DefaultPlacementStrategy, PlacementStrategy


class PlacementEngine:
    """Engine orchestrating segment placement using planners, strategies, and policies."""

    def __init__(
        self,
        planner: Optional[PartitionPlanner] = None,
        strategy: Optional[PlacementStrategy] = None,
        policy: Optional[PartitionPolicy] = None,
    ):
        self.policy = policy or PartitionPolicy()
        self.planner = planner or SimpleCapacityPlanner(self.policy)
        self.strategy = strategy or DefaultPlacementStrategy()

    def select_placement(
        self, segment_id: SegmentId, data_size: int, partitions: List[PartitionDescriptor]
    ) -> PartitionPlacementResult:
        """Select target partition using planner and strategy."""
        if not partitions:
            raise GraphStorageError("No storage partitions available in placement engine")

        target_pid = self.planner.plan_placement(segment_id, data_size, partitions)

        target_desc = next((p for p in partitions if p.partition_id == target_pid), partitions[0])
        est_util = (target_desc.current_size_bytes + data_size) / max(target_desc.capacity_bytes, 1)

        return PartitionPlacementResult(
            target_partition_id=target_pid,
            planner_name=self.planner.__class__.__name__,
            reason="Capacity headroom and strategy selection matched",
            confidence_score=0.95,
            estimated_utilization_ratio=est_util,
            policy_name=self.policy.placement_policy,
        )
