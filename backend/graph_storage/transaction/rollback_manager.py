"""
RollbackManager implementation.
"""

from typing import Optional

from graph_storage.cache.cache_manager import CacheManager
from graph_storage.model import SegmentId
from graph_storage.segment.segment_repository import SegmentRepository
from graph_storage.transaction.transaction_context import TransactionContext
from graph_storage.transaction.transaction_log import TransactionJournal


class RollbackManager:
    """Rollback manager for undoing write_set changes and restoring before images."""

    def __init__(
        self,
        segment_repository: Optional[SegmentRepository] = None,
        cache_manager: Optional[CacheManager] = None,
        journal: Optional[TransactionJournal] = None,
    ):
        self.segment_repository = segment_repository
        self.cache_manager = cache_manager
        self.journal = journal

    def undo(self, ctx: TransactionContext) -> bool:
        """Rollback all modifications recorded in transaction write set."""
        for write_entry in ctx.write_set.entries():
            key = write_entry.key
            before_image = write_entry.before_image

            # Restore before image in segment repository if available
            if self.segment_repository:
                seg_id = SegmentId(key)
                if before_image is not None:
                    self.segment_repository.save(seg_id, before_image)
                else:
                    if self.segment_repository.exists(seg_id):
                        self.segment_repository.delete(seg_id)

            # Invalidate cache entry
            if self.cache_manager:
                self.cache_manager.invalidate(key)

        if self.journal:
            self.journal.append(
                transaction_id=ctx.transaction_id.value,
                operation="ROLLBACK",
                state="ROLLED_BACK",
                metadata={"write_count": str(len(ctx.write_set.keys()))},
            )

        return True
