"""
Unit tests for Segment Storage subsystem (Step 4.4 Refinements).
"""

import unittest
from graph_storage.backend import MemoryBackend
from graph_storage.exceptions import GraphStorageError
from graph_storage.model import SegmentId
from graph_storage.segment import (
    ChecksumAlgorithm,
    IntegrityVerifier,
    SegmentLifecycleManager,
    SegmentManager,
    SegmentMetadataFactory,
    SegmentRepository,
    SegmentState,
    SegmentStateMachine,
    SegmentValidator,
)


class TestIntegrityVerifierAndMetadata(unittest.TestCase):
    """Test suite for IntegrityVerifier and SegmentMetadataFactory."""

    def test_checksum_generation_and_verification(self):
        payload = b"test payload for integrity verifier"
        checksum = IntegrityVerifier.generate_checksum(payload, ChecksumAlgorithm.SHA256)
        self.assertTrue(IntegrityVerifier.verify_checksum(payload, checksum, ChecksumAlgorithm.SHA256))
        self.assertFalse(IntegrityVerifier.verify_checksum(payload, "invalid_hash"))

    def test_metadata_factory(self):
        seg_id = SegmentId("seg_meta_test")
        payload = b"metadata factory test payload"
        metadata = SegmentMetadataFactory.create_metadata(seg_id, payload)
        self.assertEqual(metadata.segment_id, seg_id)
        self.assertEqual(metadata.size_bytes, len(payload))
        self.assertTrue(IntegrityVerifier.verify_checksum(payload, metadata.checksum))


class TestSegmentStateMachine(unittest.TestCase):
    """Test suite for SegmentStateMachine."""

    def test_state_transitions(self):
        sm = SegmentStateMachine()
        seg_id = SegmentId("sm_seg_1")

        self.assertEqual(sm.get_state(seg_id), SegmentState.CREATED)
        sm.transition(seg_id, SegmentState.ACTIVE)
        self.assertEqual(sm.get_state(seg_id), SegmentState.ACTIVE)
        sm.transition(seg_id, SegmentState.ARCHIVED)
        self.assertEqual(sm.get_state(seg_id), SegmentState.ARCHIVED)

    def test_illegal_state_transition_raises_error(self):
        sm = SegmentStateMachine()
        seg_id = SegmentId("sm_seg_bad")
        sm.transition(seg_id, SegmentState.ACTIVE)
        sm.transition(seg_id, SegmentState.DELETED)
        with self.assertRaises(GraphStorageError):
            sm.transition(seg_id, SegmentState.ACTIVE)


class TestSegmentManagerFacadeAndRepository(unittest.TestCase):
    """Test suite for SegmentManager facade, services, and SegmentRepository."""

    def setUp(self):
        self.backend = MemoryBackend()
        self.manager = SegmentManager(self.backend)

    def test_facade_delegation(self):
        seg_id = SegmentId("seg_facade_1")
        payload = b"facade payload"

        descriptor = self.manager.create_segment(seg_id, payload)
        self.assertEqual(descriptor.metadata.segment_id, seg_id)
        self.assertTrue(self.manager.segment_exists(seg_id))
        self.assertEqual(self.manager.load_segment(seg_id), payload)

        stats = self.manager.statistics()
        self.assertEqual(stats["total_segments"], 1)
        self.assertEqual(stats["total_bytes"], len(payload))

        self.assertTrue(self.manager.delete_segment(seg_id))
        self.assertFalse(self.manager.segment_exists(seg_id))


class TestSegmentLifecycleManager(unittest.TestCase):
    """Test suite for SegmentLifecycleManager transitions."""

    def setUp(self):
        self.backend = MemoryBackend()
        self.manager = SegmentManager(self.backend)
        self.lifecycle = SegmentLifecycleManager(self.manager)

    def test_lifecycle_transitions(self):
        seg_id = SegmentId("life_001")
        payload1 = b"original data"
        payload2 = b"replaced data"

        self.lifecycle.create(seg_id, payload1)
        self.assertEqual(self.lifecycle.get_state(seg_id), SegmentState.ACTIVE)
        self.assertEqual(self.manager.load_segment(seg_id), payload1)

        self.lifecycle.replace(seg_id, payload2)
        self.assertEqual(self.lifecycle.get_state(seg_id), SegmentState.REPLACED)

        self.assertTrue(self.lifecycle.archive(seg_id))
        self.assertEqual(self.lifecycle.get_state(seg_id), SegmentState.ARCHIVED)

        self.assertTrue(self.lifecycle.recover(seg_id))
        self.assertEqual(self.lifecycle.get_state(seg_id), SegmentState.ACTIVE)

        self.assertTrue(self.lifecycle.delete(seg_id))
        self.assertEqual(self.lifecycle.get_state(seg_id), SegmentState.DELETED)


if __name__ == "__main__":
    unittest.main()
