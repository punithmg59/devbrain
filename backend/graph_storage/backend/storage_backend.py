"""
StorageBackend abstract interface.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List


class StorageBackend(ABC):
    """Abstract interface for physical storage backends."""

    @abstractmethod
    def exists(self, key: str) -> bool:
        """Check if an artifact exists in storage."""
        ...

    @abstractmethod
    def read(self, key: str) -> bytes:
        """Read data bytes for the given storage key."""
        ...

    @abstractmethod
    def write(self, key: str, data: bytes) -> None:
        """Write data bytes to the given storage key."""
        ...

    @abstractmethod
    def delete(self, key: str) -> bool:
        """Delete an artifact by storage key."""
        ...

    @abstractmethod
    def list(self, prefix: str = "") -> List[str]:
        """List all storage keys matching the given prefix."""
        ...

    @abstractmethod
    def health(self) -> Dict[str, Any]:
        """Retrieve operational health details of the storage backend."""
        ...
