"""
EvictionStrategy abstract interface and LRUEvictionStrategy implementation.
"""

from abc import ABC, abstractmethod
from typing import List

from graph_storage.cache.cache_entry import CacheEntry


class EvictionStrategy(ABC):
    """Abstract strategy interface for selecting cache entries for eviction."""

    @abstractmethod
    def select_eviction_candidates(self, entries: List[CacheEntry], count: int) -> List[str]:
        """Select keys of cache entries to evict."""
        ...


class LRUEvictionStrategy(EvictionStrategy):
    """Least Recently Used (LRU) eviction strategy."""

    def select_eviction_candidates(self, entries: List[CacheEntry], count: int) -> List[str]:
        if not entries or count <= 0:
            return []

        # Sort entries by last_access_time ascending (oldest access first)
        sorted_entries = sorted(entries, key=lambda e: (e.priority, e.last_access_time))
        return [e.cache_key for e in sorted_entries[:count]]
