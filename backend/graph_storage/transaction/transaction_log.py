"""
TransactionJournal and TransactionLog implementation.
"""

import threading
import time
from dataclasses import dataclass, field
from typing import Dict, List


@dataclass(frozen=True)
class JournalEntry:
    """Immutable journal entry recording a transaction state change or operation."""

    transaction_id: str
    timestamp: float
    operation: str
    state: str
    metadata: Dict[str, str] = field(default_factory=dict)


class TransactionJournal:
    """Append-only transaction journal for recovery and auditing."""

    def __init__(self):
        self._entries: List[JournalEntry] = []
        self._checkpoints: List[int] = []
        self._lock = threading.RLock()

    def append(self, transaction_id: str, operation: str, state: str, metadata: Dict[str, str] = None) -> JournalEntry:
        """Append a new log entry to the journal."""
        entry = JournalEntry(
            transaction_id=transaction_id,
            timestamp=time.time(),
            operation=operation,
            state=state,
            metadata=metadata or {},
        )
        with self._lock:
            self._entries.append(entry)
        return entry

    def read(self, limit: int = 100) -> List[JournalEntry]:
        """Read latest journal entries."""
        with self._lock:
            return list(self._entries[-limit:])

    def entries_for_tx(self, transaction_id: str) -> List[JournalEntry]:
        """Retrieve all journal entries for a given transaction ID."""
        with self._lock:
            return [e for e in self._entries if e.transaction_id == transaction_id]

    def checkpoint(self) -> int:
        """Record a checkpoint index."""
        with self._lock:
            cp_idx = len(self._entries)
            self._checkpoints.append(cp_idx)
            return cp_idx

    def truncate(self, up_to_index: int) -> None:
        """Truncate journal entries up to index."""
        with self._lock:
            self._entries = self._entries[up_to_index:]

    def archive(self) -> List[JournalEntry]:
        """Return full journal entries for archiving."""
        with self._lock:
            return list(self._entries)


class TransactionLog(TransactionJournal):
    """Alias for TransactionJournal."""

    pass
