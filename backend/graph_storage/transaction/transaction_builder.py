"""
TransactionBuilder for constructing TransactionContext instances.
"""

import time
from typing import Dict, Optional

from graph_storage.exceptions import GraphStorageError
from graph_storage.model import TransactionId
from graph_storage.transaction.isolation_policy import IsolationLevel
from graph_storage.transaction.transaction_context import TransactionContext
from graph_storage.transaction.transaction_sets import ReadSet, WriteSet
from graph_storage.transaction.transaction_state import TransactionState


class TransactionBuilder:
    """Builder pattern for constructing TransactionContext instances."""

    def __init__(self):
        self._transaction_id: Optional[TransactionId] = None
        self._start_time: float = time.time()
        self._status: TransactionState = TransactionState.CREATED
        self._isolation_level: IsolationLevel = IsolationLevel.READ_COMMITTED
        self._read_set: ReadSet = ReadSet()
        self._write_set: WriteSet = WriteSet()
        self._metadata: Dict[str, str] = {}
        self._parent_transaction_id: Optional[TransactionId] = None

    def set_transaction_id(self, tx_id: TransactionId) -> "TransactionBuilder":
        self._transaction_id = tx_id
        return self

    def set_start_time(self, timestamp: float) -> "TransactionBuilder":
        self._start_time = timestamp
        return self

    def set_status(self, status: TransactionState) -> "TransactionBuilder":
        self._status = status
        return self

    def set_isolation_level(self, level: IsolationLevel) -> "TransactionBuilder":
        self._isolation_level = level
        return self

    def set_read_set(self, read_set: ReadSet) -> "TransactionBuilder":
        self._read_set = read_set
        return self

    def set_write_set(self, write_set: WriteSet) -> "TransactionBuilder":
        self._write_set = write_set
        return self

    def set_metadata(self, metadata: Dict[str, str]) -> "TransactionBuilder":
        self._metadata = dict(metadata)
        return self

    def set_parent_transaction_id(self, parent_id: Optional[TransactionId]) -> "TransactionBuilder":
        self._parent_transaction_id = parent_id
        return self

    def build(self) -> TransactionContext:
        """Construct and validate TransactionContext."""
        if not self._transaction_id:
            raise GraphStorageError("TransactionId is required for TransactionBuilder")

        return TransactionContext(
            transaction_id=self._transaction_id,
            start_time=self._start_time,
            status=self._status,
            isolation_level=self._isolation_level,
            read_set=self._read_set,
            write_set=self._write_set,
            metadata=self._metadata,
            parent_transaction_id=self._parent_transaction_id,
        )
