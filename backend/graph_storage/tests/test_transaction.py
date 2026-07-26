"""
Unit tests for Transaction & Consistency Engine Subsystem (Step 4.9).
"""

import unittest
from graph_storage.backend import MemoryBackend
from graph_storage.cache import CacheManager
from graph_storage.exceptions import GraphStorageError
from graph_storage.model import SegmentId, TransactionId
from graph_storage.segment import SegmentRepository
from graph_storage.transaction import (
    ConflictDetector,
    ConsistencyValidator,
    IsolationLevel,
    IsolationPolicy,
    LockManager,
    LockType,
    RecoveryManager,
    RollbackManager,
    TransactionBuilder,
    TransactionContext,
    TransactionJournal,
    TransactionManager,
    TransactionState,
    TransactionStateMachine,
    WriteSet,
)


class TestTransactionStateMachineAndJournal(unittest.TestCase):
    """Test suite for TransactionStateMachine, LockManager, and TransactionJournal."""

    def test_state_machine_transitions(self):
        sm = TransactionStateMachine(initial_state=TransactionState.CREATED)
        self.assertEqual(sm.current_state, TransactionState.CREATED)

        sm.transition(TransactionState.ACTIVE)
        self.assertEqual(sm.current_state, TransactionState.ACTIVE)

        sm.transition(TransactionState.PREPARING)
        sm.transition(TransactionState.COMMITTED)
        self.assertEqual(sm.current_state, TransactionState.COMMITTED)

        # Invalid transition from COMMITTED to ROLLED_BACK should raise error
        with self.assertRaises(GraphStorageError):
            sm.transition(TransactionState.ROLLED_BACK)

    def test_transaction_journal(self):
        journal = TransactionJournal()
        journal.append("tx_1", "BEGIN", "ACTIVE")
        journal.append("tx_1", "COMMIT", "COMMITTED")

        entries = journal.read(limit=10)
        self.assertEqual(len(entries), 2)
        self.assertEqual(entries[0].transaction_id, "tx_1")
        self.assertEqual(entries[1].state, "COMMITTED")

    def test_lock_manager(self):
        lm = LockManager()
        tx1 = TransactionId("tx_lock_1")
        tx2 = TransactionId("tx_lock_2")

        # Acquire exclusive lock
        self.assertTrue(lm.acquire(tx1, "key_a", LockType.EXCLUSIVE))
        self.assertTrue(lm.is_locked("key_a"))

        # Second transaction attempt should fail/timeout
        self.assertFalse(lm.acquire(tx2, "key_a", LockType.EXCLUSIVE, timeout_sec=0.05))

        lm.release(tx1, "key_a")
        self.assertFalse(lm.is_locked("key_a"))


class TestTransactionManagerAndRollback(unittest.TestCase):
    """Test suite for TransactionManager facade, RollbackManager, and Recovery."""

    def setUp(self):
        self.backend = MemoryBackend()
        self.segment_repo = SegmentRepository(self.backend)
        self.cache_manager = CacheManager()
        self.tx_manager = TransactionManager(
            segment_repository=self.segment_repo,
            cache_manager=self.cache_manager,
        )

    def test_transaction_commit_flow(self):
        ctx = self.tx_manager.begin(isolation_level=IsolationLevel.READ_COMMITTED)
        self.assertEqual(ctx.status, TransactionState.ACTIVE)

        # Record a write
        self.tx_manager.record_write(
            ctx.transaction_id, key="seg_tx_1", before_image=None, after_image=b"tx_payload_1"
        )
        self.segment_repo.save(SegmentId("seg_tx_1"), b"tx_payload_1")

        self.assertTrue(self.tx_manager.commit(ctx.transaction_id))

        # Verify data saved in segment repo
        self.assertTrue(self.segment_repo.exists(SegmentId("seg_tx_1")))

    def test_transaction_rollback_restores_before_image(self):
        # Pre-populate segment repository with initial state
        seg_id = SegmentId("seg_rollback_1")
        self.segment_repo.save(seg_id, b"original_payload")

        ctx = self.tx_manager.begin()
        self.tx_manager.record_write(
            ctx.transaction_id, key="seg_rollback_1", before_image=b"original_payload", after_image=b"new_payload"
        )
        # Modify segment
        self.segment_repo.save(seg_id, b"new_payload")

        # Execute rollback
        self.assertTrue(self.tx_manager.rollback(ctx.transaction_id))

        # Verify original payload restored
        restored = self.segment_repo.load(seg_id)
        self.assertEqual(restored, b"original_payload")

    def test_conflict_detection(self):
        ctx1 = self.tx_manager.begin()
        ctx2 = self.tx_manager.begin()

        ws1 = WriteSet()
        ws1.add("key_conflict", None, b"val1")

        ws2 = WriteSet()
        ws2.add("key_conflict", None, b"val2")
        ctx2.write_set.add("key_conflict", None, b"val2")

        conflicts = ConflictDetector.detect_conflicts(ctx1.transaction_id, ws1, [ctx2])
        self.assertEqual(len(conflicts), 1)

    def test_recovery_manager(self):
        rm = RecoveryManager(self.tx_manager.journal, self.tx_manager.coordinator.rollback_manager, self.segment_repo)
        self.tx_manager.journal.append("tx_crash_1", "BEGIN", "ACTIVE")
        self.tx_manager.journal.append("tx_crash_2", "COMMIT", "COMMITTED")

        recovered = rm.recover()
        self.assertGreaterEqual(recovered, 1)


if __name__ == "__main__":
    unittest.main()
