"""
TransactionArbiter abstract interface.
"""

from abc import ABC, abstractmethod
from graph_storage.model import SnapshotId, StorageKey, TransactionHandle, LeaseHandle


class TransactionArbiter(ABC):
    """Abstract interface for coordinating storage transactions and lease locks."""

    @abstractmethod
    def begin_read(self, snapshot_id: SnapshotId) -> TransactionHandle:
        """Begin an isolated read transaction for a specific snapshot."""
        ...

    @abstractmethod
    def begin_write(self, snapshot_id: SnapshotId) -> TransactionHandle:
        """Begin an isolated write transaction for a specific snapshot."""
        ...

    @abstractmethod
    def acquire_lease(self, resource_key: StorageKey, ttl_seconds: float) -> LeaseHandle:
        """Acquire a temporary lease lock handle for a storage resource."""
        ...

    @abstractmethod
    def release_lease(self, lease_handle: LeaseHandle) -> bool:
        """Release a previously acquired resource lease handle."""
        ...
