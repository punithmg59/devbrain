"""
Unit tests for Snapshot & Manifest Management subsystem (Step 4.6 Refinements).
"""

import unittest
from graph_storage.backend import MemoryBackend
from graph_storage.exceptions import GraphStorageError, SegmentNotFoundError
from graph_storage.manifest import (
    ManifestBuilder,
    ManifestDescriptor,
    ManifestIndex,
    ManifestManager,
    ManifestRepository,
    SnapshotBuilder,
    SnapshotDescriptor,
    SnapshotGraph,
    SnapshotHistory,
    SnapshotManager,
    SnapshotPolicy,
    SnapshotRepository,
    SnapshotValidator,
)
from graph_storage.model import (
    PartitionId,
    SegmentDescriptor,
    SegmentId,
    SegmentMetadata,
    SnapshotId,
    StorageKey,
    VersionRef,
)
from graph_storage.segment import SegmentRepository


class TestSnapshotBuildersAndIndex(unittest.TestCase):
    """Test suite for SnapshotBuilder, ManifestBuilder, SnapshotGraph, and ManifestIndex."""

    def test_snapshot_builder(self):
        sid = SnapshotId("snap_b_1")
        key = StorageKey("m_b_1")
        builder = (
            SnapshotBuilder()
            .set_snapshot_id(sid)
            .set_repository_id("repo_b")
            .set_manifest_location(key)
            .set_segment_count(5)
            .set_total_size(1024)
        )

        descriptor = builder.build()
        self.assertEqual(descriptor.snapshot_id, sid)
        self.assertEqual(descriptor.repository_id, "repo_b")
        self.assertEqual(descriptor.segment_count, 5)

    def test_manifest_builder_sorting_and_deduplication(self):
        sid = SnapshotId("snap_mb_1")
        seg1 = SegmentDescriptor(
            metadata=SegmentMetadata(
                segment_id=SegmentId("b_seg"),
                partition_id=PartitionId("default"),
                size_bytes=10,
                record_count=1,
                checksum="c1",
            ),
            storage_key=StorageKey("k1"),
        )
        seg2 = SegmentDescriptor(
            metadata=SegmentMetadata(
                segment_id=SegmentId("a_seg"),
                partition_id=PartitionId("default"),
                size_bytes=20,
                record_count=1,
                checksum="c2",
            ),
            storage_key=StorageKey("k2"),
        )

        # Add in reverse order with duplicate
        builder = (
            ManifestBuilder()
            .set_manifest_id("m_b_test")
            .set_snapshot_id(sid)
            .add_segment_entry(seg1)
            .add_segment_entry(seg2)
            .add_segment_entry(seg1)  # duplicate
        )

        manifest = builder.build()
        self.assertEqual(len(manifest.segment_entries), 2)
        # Verify deterministic sorting by segment_id ("a_seg" before "b_seg")
        self.assertEqual(manifest.segment_entries[0].metadata.segment_id.value, "a_seg")
        self.assertEqual(manifest.segment_entries[1].metadata.segment_id.value, "b_seg")

    def test_snapshot_graph_dag(self):
        sg = SnapshotGraph()
        sid1 = SnapshotId("snap_dag_1")
        sid2 = SnapshotId("snap_dag_2")

        desc1 = (
            SnapshotBuilder()
            .set_snapshot_id(sid1)
            .set_repository_id("repo_dag")
            .set_manifest_location(StorageKey("m1"))
            .build()
        )
        desc2 = (
            SnapshotBuilder()
            .set_snapshot_id(sid2)
            .set_repository_id("repo_dag")
            .set_manifest_location(StorageKey("m2"))
            .set_parent_snapshot_id(sid1)
            .build()
        )

        sg.register_snapshot(desc1)
        sg.register_snapshot(desc2)

        self.assertEqual(sg.parent(sid2).snapshot_id, sid1)
        self.assertTrue(sg.is_ancestor(sid1, sid2))
        self.assertTrue(sg.is_descendant(sid2, sid1))


class TestSnapshotAndManifestManagement(unittest.TestCase):
    """Test suite for SnapshotManager, ManifestManager, and Repositories."""

    def setUp(self):
        self.backend = MemoryBackend()
        self.segment_repo = SegmentRepository(self.backend)
        self.manifest_repo = ManifestRepository(self.segment_repo)
        self.snapshot_repo = SnapshotRepository(self.segment_repo)
        self.snapshot_manager = SnapshotManager(
            self.snapshot_repo, self.manifest_repo, self.segment_repo
        )

        self.seg_id_1 = SegmentId("seg_snap_001")
        self.seg_data_1 = b"dummy segment data payload 1"
        self.descriptor_1 = self.segment_repo.save(self.seg_id_1, self.seg_data_1)

        self.seg_id_2 = SegmentId("seg_snap_002")
        self.seg_data_2 = b"dummy segment data payload 2"
        self.descriptor_2 = self.segment_repo.save(self.seg_id_2, self.seg_data_2)

    def test_create_and_load_snapshot(self):
        repo_id = "repo_devbrain_1"
        snapshot = self.snapshot_manager.create_snapshot(
            repository_id=repo_id,
            segment_entries=[self.descriptor_1, self.descriptor_2],
            version=VersionRef(1, 0, 0),
        )

        self.assertEqual(snapshot.repository_id, repo_id)
        self.assertEqual(snapshot.segment_count, 2)
        self.assertEqual(snapshot.total_size, len(self.seg_data_1) + len(self.seg_data_2))

        loaded = self.snapshot_manager.load_snapshot(snapshot.snapshot_id)
        self.assertEqual(loaded.snapshot_id, snapshot.snapshot_id)
        self.assertEqual(loaded.manifest_location, snapshot.manifest_location)

    def test_manifest_validation_missing_segment_raises_error(self):
        missing_seg_id = SegmentId("missing_segment_999")
        missing_descriptor = SegmentDescriptor(
            metadata=SegmentMetadata(
                segment_id=missing_seg_id,
                partition_id=PartitionId("default"),
                size_bytes=100,
                record_count=1,
                checksum="dummy",
            ),
            storage_key=StorageKey("mem://missing"),
        )

        with self.assertRaises(SegmentNotFoundError):
            self.snapshot_manager.create_snapshot(
                repository_id="repo_missing_test",
                segment_entries=[missing_descriptor],
            )

    def test_snapshot_history_and_latest(self):
        repo_id = "repo_history_test"

        snap1 = self.snapshot_manager.create_snapshot(
            repository_id=repo_id, segment_entries=[self.descriptor_1]
        )
        snap2 = self.snapshot_manager.create_snapshot(
            repository_id=repo_id,
            segment_entries=[self.descriptor_1, self.descriptor_2],
            parent_snapshot_id=snap1.snapshot_id,
        )

        latest = self.snapshot_manager.latest_snapshot(repo_id)
        self.assertIsNotNone(latest)
        self.assertEqual(latest.snapshot_id, snap2.snapshot_id)

        history = self.snapshot_manager.list_snapshots(repo_id)
        self.assertEqual(len(history), 2)

    def test_delete_snapshot(self):
        repo_id = "repo_delete_test"
        snap = self.snapshot_manager.create_snapshot(
            repository_id=repo_id, segment_entries=[self.descriptor_1]
        )

        self.assertTrue(self.snapshot_manager.snapshot_exists(snap.snapshot_id))
        self.assertTrue(self.snapshot_manager.delete_snapshot(snap.snapshot_id))
        self.assertFalse(self.snapshot_manager.snapshot_exists(snap.snapshot_id))


if __name__ == "__main__":
    unittest.main()
