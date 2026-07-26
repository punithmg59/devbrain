"""
CommitCoordinator implementing Prepare, Validation, Commit, and Cleanup phases.
"""

from typing import List, Optional
from graph_storage.cache.cache_manager import CacheManager
from graph_storage.exceptions import GraphStorageError
from graph_storage.transaction.conflict_detector import ConflictDetector
from graph_storage.transaction.consistency_validator import ConsistencyValidator
from graph_storage.transaction.lock_manager import LockManager
from graph_storage.transaction.rollback_manager import RollbackManager
from graph_storage.transaction.transaction_context import TransactionContext
from graph_storage.transaction.transaction_log import TransactionJournal


class CommitCoordinator:
    """Coordinator executing single-node commit phases."""

    def __init__(
        self,
        lock_manager: LockManager,
        rollback_manager: RollbackManager,
        journal: TransactionJournal,
        cache_manager: Optional[CacheManager] = None,
    ):
        self.lock_manager = lock_manager
        self.rollback_manager = rollback_manager
        self.journal = journal
        self.cache_manager = cache_manager

    def execute_commit(self, ctx: TransactionContext, active_txs: List[TransactionContext]) -> bool:
        """Execute single-node prepare, validate, commit, and cleanup phases."""
        # 1. Prepare Phase
        self.journal.append(ctx.transaction_id.value, "PREPARE", "PREPARING")

        # 2. Validation Phase
        ConsistencyValidator.validate_cross_layer_consistency(ctx, active_txs)
        conflicts = ConflictDetector.detect_conflicts(ctx.transaction_id, ctx.write_set, active_txs)
        if conflicts:
            raise GraphStorageError(f"Transaction commit failed due to conflicts: {', '.join(conflicts)}")

        # 3. Commit Phase
        self.journal.append(ctx.transaction_id.value, "COMMIT", "COMMITTED")

        # Invalidate/update cache for modified keys
        if self.cache_manager:
            for write_entry in ctx.write_set.entries():
                if write_entry.after_image is not None:
                    self.cache_manager.put(write_entry.key, write_entry.after_image)

        # 4. Cleanup Phase
        self.lock_manager.release_all(ctx.transaction_id)
        return True
