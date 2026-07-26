"""
Unit tests for Snapshot & Manifest Management subsystem (Step 4.6).
"""

import unittest
from graph_storage.backend import MemoryBackend
from graph_storage.exceptions import GraphStorageError, SegmentNotFoundError
from graph_storage.manifest import (
    ManifestDescriptor,
    ManifestManager,
    ManifestRepository,
    SnapshotDescriptor,
    SnapshotHistory,
    SnapshotManager,
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

        # Create dummy segment in segment_repo
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

        # Load snapshot
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
        self.assertEqual(history[0].snapshot_id, snap1.snapshot_id)
        self.assertEqual(history[1].snapshot_id, snap2.snapshot_id)

        # Ancestry resolution
        history_tracker = SnapshotHistory(self.snapshot_repo)
        ancestors = history_tracker.get_ancestors(snap2.snapshot_id)
        self.assertEqual(len(ancestors), 2)
        self.assertEqual(ancestors[0].snapshot_id, snap1.snapshot_id)
        self.assertEqual(ancestors[1].snapshot_id, snap2.snapshot_id)

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
