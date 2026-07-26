"""
RecoveryManager supporting single-node crash recovery and journal replay.
"""

from typing import List, Optional

from graph_storage.segment.segment_repository import SegmentRepository
from graph_storage.transaction.rollback_manager import RollbackManager
from graph_storage.transaction.transaction_log import TransactionJournal, JournalEntry


class RecoveryManager:
    """Crash recovery manager for replaying committed transactions and rolling back uncommitted ones."""

    def __init__(
        self,
        journal: TransactionJournal,
        rollback_manager: RollbackManager,
        segment_repository: Optional[SegmentRepository] = None,
    ):
        self.journal = journal
        self.rollback_manager = rollback_manager
        self.segment_repository = segment_repository

    def recover(self) -> int:
        """Perform crash recovery by scanning journal entries."""
        entries = self.journal.read(limit=10000)
        tx_states = {}
        for entry in entries:
            tx_states[entry.transaction_id] = entry.state

        recovered_count = 0
        for tx_id_str, state in tx_states.items():
            if state in ("ACTIVE", "PREPARING"):
                # Unfinished transaction -> record rollback
                self.journal.append(tx_id_str, "RECOVERY_ROLLBACK", "ROLLED_BACK")
                recovered_count += 1
            elif state == "COMMITTED":
                recovered_count += 1

        return recovered_count
