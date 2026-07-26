"""
Unit tests for Partitioning Subsystem (Step 4.7 Refinements).
"""

import unittest
from graph_storage.exceptions import GraphStorageError
from graph_storage.model import PartitionId, SegmentId
from graph_storage.partitioning import (
    CapacityModel,
    DefaultPartitionRepository,
    DefaultPlacementStrategy,
    MigrationStep,
    PartitionBalancer,
    PartitionBuilder,
    PartitionIndex,
    PartitionManager,
    PartitionMetrics,
    PartitionPlacementResult,
    PartitionPolicy,
    PartitionTopology,
    PartitionValidator,
    PlacementEngine,
    RebalancePlan,
    SimpleCapacityPlanner,
)


class TestPartitionBuilderAndValidator(unittest.TestCase):
    """Test suite for PartitionBuilder and PartitionValidator."""

    def test_partition_builder(self):
        pid = PartitionId("p_01")
        builder = (
            PartitionBuilder()
            .set_partition_id(pid)
            .set_partition_name("partition_alpha")
            .set_capacity_bytes(1048576)
            .set_current_size_bytes(512)
        )
        desc = builder.build()

        self.assertEqual(desc.partition_id, pid)
        self.assertEqual(desc.partition_name, "partition_alpha")
        self.assertEqual(desc.capacity_bytes, 1048576)

    def test_partition_topology_and_engine(self):
        topology = PartitionTopology()
        p1 = (
            PartitionBuilder()
            .set_partition_id(PartitionId("p1"))
            .set_capacity_bytes(1000)
            .set_current_size_bytes(100)
            .build()
        )
        topology.register_partition(p1, zone="us-east-1")

        self.assertEqual(topology.zone(PartitionId("p1")), "us-east-1")
        self.assertEqual(len(topology.hierarchy()["us-east-1"]), 1)

        engine = PlacementEngine()
        result = engine.select_placement(SegmentId("s_engine_1"), 200, [p1])
        self.assertIsInstance(result, PartitionPlacementResult)
        self.assertEqual(result.target_partition_id, PartitionId("p1"))

    def test_rebalance_plan(self):
        step = MigrationStep("p1", "p2", "seg_1", 100)
        plan = RebalancePlan([step], 1.0, 0.2, True, "Test Plan")
        self.assertEqual(len(plan.steps), 1)
        self.assertTrue(plan.validation_result)


class TestPartitionManager(unittest.TestCase):
    """Test suite for PartitionManager facade and PlacementEngine integration."""

    def setUp(self):
        self.manager = PartitionManager()

    def test_manager_placement_and_rebalance(self):
        pid = PartitionId("p_mgr_1")
        self.manager.create_partition(pid, "Manager Partition 1", capacity_bytes=2000, zone="zone_a")

        result = self.manager.select_placement(SegmentId("s1"), 500)
        self.assertEqual(result.target_partition_id, pid)

        plan = self.manager.generate_rebalance_plan()
        self.assertIsInstance(plan, RebalancePlan)


if __name__ == "__main__":
    unittest.main()
