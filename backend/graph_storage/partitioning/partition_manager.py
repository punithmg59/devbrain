"""
PartitionManager facade orchestrating partitioning topology, placement engine, and repository operations.
"""

from typing import Dict, List, Optional

from graph_storage.exceptions import GraphStorageError
from graph_storage.model import PartitionId, SegmentId
from graph_storage.partitioning.partition_balancer import PartitionBalancer
from graph_storage.partitioning.partition_builder import PartitionBuilder
from graph_storage.partitioning.partition_descriptor import PartitionDescriptor
from graph_storage.partitioning.partition_index import PartitionIndex
from graph_storage.partitioning.partition_planner import PartitionPlanner
from graph_storage.partitioning.partition_policy import PartitionPolicy
from graph_storage.partitioning.partition_repository import DefaultPartitionRepository, PartitionRepository
from graph_storage.partitioning.partition_topology import PartitionTopology
from graph_storage.partitioning.partition_validator import PartitionValidator
from graph_storage.partitioning.placement_engine import PlacementEngine
from graph_storage.partitioning.placement_result import PartitionPlacementResult
from graph_storage.partitioning.placement_strategy import PlacementStrategy
from graph_storage.partitioning.rebalance_plan import MigrationStep, RebalancePlan
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
        self.placement_engine = PlacementEngine(planner, placement_strategy, self.policy)
        self.balancer = PartitionBalancer(self.policy)
        self.topology = PartitionTopology()
        self.index = PartitionIndex()

        # Sync index & topology
        for p in self.repository.list():
            self.index.index_partition(p)
            self.topology.register_partition(p)

    def create_partition(
        self,
        partition_id: PartitionId,
        partition_name: str,
        capacity_bytes: int = 1073741824,
        zone: str = "default_zone",
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
        self.topology.register_partition(descriptor, zone=zone)
        return descriptor

    def select_placement(self, segment_id: SegmentId, data_size: int) -> PartitionPlacementResult:
        """Select target partition using PlacementEngine."""
        partitions = self.repository.list()
        return self.placement_engine.select_placement(segment_id, data_size, partitions)

    def delete_partition(self, partition_id: PartitionId) -> bool:
        """Delete a storage partition."""
        return self.repository.delete_partition(partition_id)

    def move_segment(
        self, segment_id: SegmentId, source_partition_id: PartitionId, target_partition_id: PartitionId
    ) -> bool:
        """Record a segment move between partitions."""
        self.index.map_segment(segment_id, target_partition_id)
        return True

    def generate_rebalance_plan(self) -> RebalancePlan:
        """Generate structured RebalancePlan."""
        partitions = self.repository.list()
        recs = self.balancer.recommend(partitions)
        steps = [
            MigrationStep(
                source_partition_id=r.source_partition_id,
                target_partition_id=r.target_partition_id,
                segment_id="sample_segment",
                size_bytes=r.estimated_transfer_bytes,
            )
            for r in recs
        ]
        return RebalancePlan(
            steps=steps,
            estimated_cost_seconds=1.5,
            estimated_benefit_ratio=0.25,
            validation_result=True,
            description=f"Plan generated with {len(steps)} migration step(s)",
        )

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
