"""
Unit tests for Partitioning Subsystem (Step 4.7).
"""

import unittest
from graph_storage.exceptions import GraphStorageError
from graph_storage.model import PartitionId, SegmentId
from graph_storage.partitioning import (
    DefaultPartitionRepository,
    DefaultPlacementStrategy,
    PartitionBalancer,
    PartitionBuilder,
    PartitionIndex,
    PartitionManager,
    PartitionPolicy,
    PartitionValidator,
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
        self.assertEqual(desc.current_size_bytes, 512)

    def test_builder_exceed_capacity_raises_error(self):
        pid = PartitionId("p_err")
        with self.assertRaises(GraphStorageError):
            (
                PartitionBuilder()
                .set_partition_id(pid)
                .set_capacity_bytes(100)
                .set_current_size_bytes(200)
                .build()
            )

    def test_partition_validator(self):
        pid = PartitionId("p_val")
        desc = (
            PartitionBuilder()
            .set_partition_id(pid)
            .set_capacity_bytes(1000)
            .set_current_size_bytes(500)
            .build()
        )

        PartitionValidator.validate_descriptor(desc)
        PartitionValidator.validate_capacity(desc, additional_bytes=400)

        with self.assertRaises(GraphStorageError):
            PartitionValidator.validate_capacity(desc, additional_bytes=600)


class TestPlacementPlannerAndBalancer(unittest.TestCase):
    """Test suite for PlacementStrategy, CapacityPlanner, and PartitionBalancer."""

    def setUp(self):
        self.p1 = (
            PartitionBuilder()
            .set_partition_id(PartitionId("p1"))
            .set_capacity_bytes(1000)
            .set_current_size_bytes(800)  # 80% full
            .build()
        )
        self.p2 = (
            PartitionBuilder()
            .set_partition_id(PartitionId("p2"))
            .set_capacity_bytes(1000)
            .set_current_size_bytes(200)  # 20% full
            .build()
        )

    def test_default_placement_strategy(self):
        strategy = DefaultPlacementStrategy()
        target = strategy.select_partition(SegmentId("seg_1"), [self.p1, self.p2])
        self.assertEqual(target, PartitionId("p2"))  # Lowest utilization

    def test_capacity_planner(self):
        policy = PartitionPolicy(maximum_partition_size_bytes=1000)
        planner = SimpleCapacityPlanner(policy)

        # Segment of size 100 fits in p2 (new size 300 <= 1000)
        target = planner.plan_placement(SegmentId("seg_2"), 100, [self.p1, self.p2])
        self.assertEqual(target, PartitionId("p2"))

        # Segment of size 300 exceeds p1 (800+300=1100 > 1000) but fits p2 (200+300=500)
        target2 = planner.plan_placement(SegmentId("seg_3"), 300, [self.p1, self.p2])
        self.assertEqual(target2, PartitionId("p2"))

    def test_balancer_analysis_and_recommendation(self):
        p_over = (
            PartitionBuilder()
            .set_partition_id(PartitionId("p_over"))
            .set_capacity_bytes(1000)
            .set_current_size_bytes(950)  # 95% > 90% threshold
            .build()
        )
        p_under = (
            PartitionBuilder()
            .set_partition_id(PartitionId("p_under"))
            .set_capacity_bytes(1000)
            .set_current_size_bytes(100)  # 10% < 40% threshold
            .build()
        )

        policy = PartitionPolicy(rebalance_threshold_ratio=0.90)
        balancer = PartitionBalancer(policy)

        report = balancer.analyze([p_over, p_under])
        self.assertIn("p_over", report.overutilized_partitions)
        self.assertIn("p_under", report.underutilized_partitions)

        recs = balancer.recommend([p_over, p_under])
        self.assertEqual(len(recs), 1)
        self.assertEqual(recs[0].source_partition_id, "p_over")
        self.assertEqual(recs[0].target_partition_id, "p_under")


class TestPartitionManager(unittest.TestCase):
    """Test suite for PartitionManager facade and Indexing."""

    def setUp(self):
        self.manager = PartitionManager()

    def test_manager_crud_and_index(self):
        pid = PartitionId("p_mgr_1")

        self.assertFalse(self.manager.validate_partition(pid))
        descriptor = self.manager.create_partition(pid, "Manager Partition 1", capacity_bytes=2000)
        self.assertEqual(descriptor.partition_id, pid)
        self.assertTrue(self.manager.validate_partition(pid))

        partitions = self.manager.list_partitions()
        self.assertEqual(len(partitions), 1)

        # Move segment simulation
        self.assertTrue(self.manager.move_segment(SegmentId("s1"), pid, pid))

        self.assertTrue(self.manager.delete_partition(pid))
        self.assertFalse(self.manager.validate_partition(pid))


if __name__ == "__main__":
    unittest.main()
