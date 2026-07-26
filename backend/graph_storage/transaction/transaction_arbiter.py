"""
TransactionArbiter abstract interface.
"""

from abc import ABC, abstractmethod


class TransactionArbiter(ABC):
    """Abstract interface for coordinating storage transactions and lease locks."""

    @abstractmethod
    def begin_read(self, transaction_id: str) -> str:
        """Begin a read transaction and return a transaction handle token."""
        ...

    @abstractmethod
    def begin_write(self, transaction_id: str) -> str:
        """Begin a write transaction and return a transaction handle token."""
        ...

    @abstractmethod
    def acquire_lease(self, resource_id: str, ttl_seconds: float) -> str:
        """Acquire a temporary lease lock for a storage resource."""
        ...

    @abstractmethod
    def release_lease(self, lease_id: str) -> bool:
        """Release a previously acquired resource lease lock."""
        ...
