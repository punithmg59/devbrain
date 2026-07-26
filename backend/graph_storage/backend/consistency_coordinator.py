"""
ConsistencyCoordinator abstract interface.
"""

from abc import ABC, abstractmethod
from graph_storage.model import StorageKey, LeaseHandle, ConsistencyModel


class ConsistencyCoordinator(ABC):
    """Abstract interface for managing storage consistency locks and models."""

    @abstractmethod
    def acquire_commit_lock(self, resource_key: StorageKey, timeout_seconds: float) -> LeaseHandle:
        """Acquire an exclusive commit lock handle for a storage operation."""
        ...

    @abstractmethod
    def release_commit_lock(self, lock_handle: LeaseHandle) -> bool:
        """Release a previously acquired commit lock handle."""
        ...

    @abstractmethod
    def consistency_model(self) -> ConsistencyModel:
        """Return the active consistency model enum of the storage backend."""
        ...
