"""
TransactionCoordinator coordinating Segment, Snapshot, Manifest, Partition repositories and CacheManager.
"""

from typing import Optional

from graph_storage.cache.cache_manager import CacheManager
from graph_storage.manifest.manifest_repository import ManifestRepository
from graph_storage.manifest.snapshot_repository import SnapshotRepository
from graph_storage.partitioning.partition_repository import PartitionRepository
from graph_storage.segment.segment_repository import SegmentRepository
from graph_storage.transaction.commit_coordinator import CommitCoordinator
from graph_storage.transaction.lock_manager import LockManager
from graph_storage.transaction.rollback_manager import RollbackManager
from graph_storage.transaction.transaction_context import TransactionContext
from graph_storage.transaction.transaction_log import TransactionJournal


class TransactionCoordinator:
    """Coordinates multi-repository operations during transaction commit and rollback."""

    def __init__(
        self,
        segment_repository: Optional[SegmentRepository] = None,
        snapshot_repository: Optional[SnapshotRepository] = None,
        manifest_repository: Optional[ManifestRepository] = None,
        partition_repository: Optional[PartitionRepository] = None,
        cache_manager: Optional[CacheManager] = None,
        journal: Optional[TransactionJournal] = None,
        lock_manager: Optional[LockManager] = None,
    ):
        self.segment_repository = segment_repository
        self.snapshot_repository = snapshot_repository
        self.manifest_repository = manifest_repository
        self.partition_repository = partition_repository
        self.cache_manager = cache_manager

        self.journal = journal or TransactionJournal()
        self.lock_manager = lock_manager or LockManager()
        self.rollback_manager = RollbackManager(segment_repository, cache_manager, self.journal)
        self.commit_coordinator = CommitCoordinator(self.lock_manager, self.rollback_manager, self.journal, cache_manager)

    def prepare_and_commit(self, ctx: TransactionContext, active_txs: list) -> bool:
        """Coordinate prepare and commit across all registered storage repositories."""
        return self.commit_coordinator.execute_commit(ctx, active_txs)

    def rollback_transaction(self, ctx: TransactionContext) -> bool:
        """Coordinate rollback across storage repositories."""
        res = self.rollback_manager.undo(ctx)
        self.lock_manager.release_all(ctx.transaction_id)
        return res
