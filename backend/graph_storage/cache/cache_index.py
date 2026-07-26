"""
CacheIndex query service for cache key lookup, statistics, and reverse mapping.
"""

from typing import Dict, Optional, Set
from graph_storage.cache.cache_entry import CacheEntry


class CacheIndex:
    """In-memory index for fast cache entry metadata query."""

    def __init__(self):
        self._key_map: Dict[str, CacheEntry] = {}
        self._size_map: Dict[str, int] = {}

    def index_entry(self, entry: CacheEntry) -> None:
        """Index a cache entry."""
        self._key_map[entry.cache_key] = entry
        self._size_map[entry.cache_key] = entry.size_bytes

    def remove_entry(self, key: str) -> None:
        """Remove a cache entry from index."""
        self._key_map.pop(key, None)
        self._size_map.pop(key, None)

    def lookup(self, key: str) -> Optional[CacheEntry]:
        """Look up cache entry by key."""
        return self._key_map.get(key)

    def contains(self, key: str) -> bool:
        """Check if key is indexed."""
        return key in self._key_map

    def statistics(self) -> Dict[str, int]:
        """Get aggregate index statistics."""
        return {
            "total_indexed_entries": len(self._key_map),
            "total_indexed_bytes": sum(self._size_map.values()),
        }

    def clear(self) -> None:
        """Clear index."""
        self._key_map.clear()
        self._size_map.clear()
