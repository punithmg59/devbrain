"""
ConflictDetector implementation.
"""

from typing import List
from graph_storage.model import TransactionId
from graph_storage.transaction.transaction_context import TransactionContext
from graph_storage.transaction.transaction_sets import WriteSet


class ConflictDetector:
    """Detector for write-write and read-write transaction conflicts."""

    @classmethod
    def detect_conflicts(
        self,
        tx_id: TransactionId,
        write_set: WriteSet,
        active_transactions: List[TransactionContext],
    ) -> List[str]:
        """Detect conflicts between write_set and active transactions."""
        conflicts: List[str] = []
        my_write_keys = set(write_set.keys())

        for active_tx in active_transactions:
            if active_tx.transaction_id == tx_id:
                continue

            active_write_keys = set(active_tx.write_set.keys())
            active_read_keys = set(active_tx.read_set.keys())

            # Write-Write conflict
            ww_intersection = my_write_keys.intersection(active_write_keys)
            for k in ww_intersection:
                conflicts.append(f"Write-Write conflict on key '{k}' with Transaction '{active_tx.transaction_id.value}'")

            # Read-Write conflict
            rw_intersection = my_write_keys.intersection(active_read_keys)
            for k in rw_intersection:
                conflicts.append(f"Read-Write conflict on key '{k}' with Transaction '{active_tx.transaction_id.value}'")

        return conflicts
