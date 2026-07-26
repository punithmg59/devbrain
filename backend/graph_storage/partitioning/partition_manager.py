"""
PartitionManager facade orchestrating partition creation, deletion, lookup, rebalancing, and moves.
"""

from typing import Dict, List, Optional

from graph_storage.exceptions import GraphStorageError
from graph_storage.model import PartitionId, SegmentId
from graph_storage.partitioning.partition_balancer import PartitionBalancer, RebalanceRecommendation
from graph_storage.partitioning.partition_builder import PartitionBuilder
from graph_storage.partitioning.partition_descriptor import PartitionDescriptor
from graph_storage.partitioning.partition_index import PartitionIndex
from graph_storage.partitioning.partition_planner import PartitionPlanner, SimpleCapacityPlanner
from graph_storage.partitioning.partition_policy import PartitionPolicy
from graph_storage.partitioning.partition_repository import DefaultPartitionRepository, PartitionRepository
from graph_storage.partitioning.partition_validator import PartitionValidator
from graph_storage.partitioning.placement_strategy import DefaultPlacementStrategy, PlacementStrategy
from graph_storage.segment.segment_repository import SegmentRepository


class PartitionManager:
    """Orchestrator for storage partitioning subsystem."""

    def __init__(
        self,
        repository: Optional[PartitionRepository] = None,
        planner: Optional[PartitionPlanner] = None,
        placement_strategy: Optional[PlacementStrategy] = None,
        policy: Optional[PartitionPolicy] = None,
        segment_repository: Optional[SegmentRepository] = None,
    ):
        self.repository = repository or DefaultPartitionRepository(segment_repository)
        self.policy = policy or PartitionPolicy()
        self.planner = planner or SimpleCapacityPlanner(self.policy)
        self.placement_strategy = placement_strategy or DefaultPlacementStrategy()
        self.balancer = PartitionBalancer(self.policy)
        self.index = PartitionIndex()

        # Sync index
        for p in self.repository.list():
            self.index.index_partition(p)

    def create_partition(
        self,
        partition_id: PartitionId,
        partition_name: str,
        capacity_bytes: int = 1073741824,
    ) -> PartitionDescriptor:
        """Create and persist a new storage partition."""
        if self.repository.exists(partition_id):
            raise GraphStorageError(f"Partition already exists: '{partition_id.value}'")

        descriptor = (
            PartitionBuilder()
            .set_partition_id(partition_id)
            .set_partition_name(partition_name)
            .set_capacity_bytes(capacity_bytes)
            .set_current_size_bytes(0)
            .set_segment_count(0)
            .set_status("ACTIVE")
            .build()
        )

        PartitionValidator.validate_descriptor(descriptor)
        self.repository.save_partition(descriptor)
        self.index.index_partition(descriptor)
        return descriptor

    def delete_partition(self, partition_id: PartitionId) -> bool:
        """Delete a storage partition."""
        return self.repository.delete_partition(partition_id)

    def move_segment(
        self, segment_id: SegmentId, source_partition_id: PartitionId, target_partition_id: PartitionId
    ) -> bool:
        """Record a segment move between partitions."""
        source_p = self.repository.load_partition(source_partition_id)
        target_p = self.repository.load_partition(target_partition_id)

        # Update index map
        self.index.map_segment(segment_id, target_partition_id)
        return True

    def rebalance(self) -> List[RebalanceRecommendation]:
        """Generate rebalance recommendations across active partitions."""
        partitions = self.repository.list()
        return self.balancer.recommend(partitions)

    def list_partitions(self) -> List[PartitionDescriptor]:
        """List all registered partition descriptors."""
        return self.repository.list()

    def lookup_partition(self, partition_id: PartitionId) -> Optional[PartitionDescriptor]:
        """Look up partition descriptor by ID."""
        if self.repository.exists(partition_id):
            return self.repository.load_partition(partition_id)
        return None

    def validate_partition(self, partition_id: PartitionId) -> bool:
        """Validate partition descriptor integrity."""
        try:
            desc = self.repository.load_partition(partition_id)
            PartitionValidator.validate_descriptor(desc)
            return True
        except Exception:
            return False
