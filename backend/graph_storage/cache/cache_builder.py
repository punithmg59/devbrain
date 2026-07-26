"""
CacheBuilder for constructing CacheEntry objects.
"""

import time
from typing import Optional

from graph_storage.cache.cache_entry import CacheEntry
from graph_storage.exceptions import GraphStorageError


class CacheBuilder:
    """Builder pattern for constructing validated CacheEntry instances."""

    def __init__(self):
        self._cache_key: Optional[str] = None
        self._value: Optional[bytes] = None
        self._created_time: float = time.time()
        self._last_access_time: float = self._created_time
        self._access_count: int = 1
        self._priority: int = 1
        self._ttl_seconds: float = 3600.0

    def set_cache_key(self, key: str) -> "CacheBuilder":
        self._cache_key = key
        return self

    def set_value(self, value: bytes) -> "CacheBuilder":
        self._value = value
        return self

    def set_created_time(self, timestamp: float) -> "CacheBuilder":
        self._created_time = timestamp
        return self

    def set_last_access_time(self, timestamp: float) -> "CacheBuilder":
        self._last_access_time = timestamp
        return self

    def set_access_count(self, count: int) -> "CacheBuilder":
        self._access_count = count
        return self

    def set_priority(self, priority: int) -> "CacheBuilder":
        self._priority = priority
        return self

    def set_ttl_seconds(self, ttl: float) -> "CacheBuilder":
        self._ttl_seconds = ttl
        return self

    def build(self) -> CacheEntry:
        """Construct and validate CacheEntry."""
        if not self._cache_key:
            raise GraphStorageError("CacheKey is required for CacheBuilder")
        if self._value is None:
            raise GraphStorageError("Value is required for CacheBuilder")

        size_bytes = len(self._value)
        expiration = self._created_time + self._ttl_seconds if self._ttl_seconds > 0 else 0.0

        return CacheEntry(
            cache_key=self._cache_key,
            value=self._value,
            created_time=self._created_time,
            last_access_time=self._last_access_time,
            access_count=self._access_count,
            size_bytes=size_bytes,
            priority=self._priority,
            ttl_seconds=self._ttl_seconds,
            expiration_time=expiration,
        )
