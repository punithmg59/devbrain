"""
SegmentCache abstract interface.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional


class SegmentCache(ABC):
    """Abstract interface for storage segment caching."""

    @abstractmethod
    def get(self, segment_id: str) -> Optional[bytes]:
        """Retrieve a cached storage segment by ID if present."""
        ...

    @abstractmethod
    def put(self, segment_id: str, data: bytes) -> None:
        """Insert or update a storage segment in the cache."""
        ...

    @abstractmethod
    def invalidate(self, segment_id: str) -> bool:
        """Invalidate and evict a specific storage segment from cache."""
        ...

    @abstractmethod
    def clear(self) -> None:
        """Clear all cached storage segments."""
        ...

    @abstractmethod
    def statistics(self) -> Dict[str, Any]:
        """Retrieve cache metrics and resource utilization statistics."""
        ...
