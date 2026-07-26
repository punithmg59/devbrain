"""
ConsistencyCoordinator abstract interface.
"""

from abc import ABC, abstractmethod


class ConsistencyCoordinator(ABC):
    """Abstract interface for managing storage consistency locks and models."""

    @abstractmethod
    def acquire_commit_lock(self, lock_id: str, timeout_seconds: float) -> str:
        """Acquire an exclusive commit lock for a storage operation."""
        ...

    @abstractmethod
    def release_commit_lock(self, lock_handle: str) -> bool:
        """Release a previously acquired commit lock."""
        ...

    @abstractmethod
    def consistency_model(self) -> str:
        """Return the consistency model description for the backend."""
        ...
