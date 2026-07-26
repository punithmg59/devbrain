"""
SegmentCache abstract interface.
"""

from abc import ABC, abstractmethod
from typing import Optional
from graph_storage.model import SegmentId, CacheStatistics


class SegmentCache(ABC):
    """Abstract interface for storage segment caching."""

    @abstractmethod
    def get(self, segment_id: SegmentId) -> Optional[bytes]:
        """Retrieve cached segment bytes by ID if present."""
        ...

    @abstractmethod
    def put(self, segment_id: SegmentId, data: bytes) -> None:
        """Insert or update a storage segment in the cache."""
        ...

    @abstractmethod
    def invalidate(self, segment_id: SegmentId) -> bool:
        """Invalidate and evict a specific storage segment from cache."""
        ...

    @abstractmethod
    def clear(self) -> None:
        """Clear all cached storage segments."""
        ...

    @abstractmethod
    def statistics(self) -> CacheStatistics:
        """Retrieve cache metrics and utilization statistics."""
        ...
