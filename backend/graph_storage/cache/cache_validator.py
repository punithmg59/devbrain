"""
CacheValidator for checking TTL expiration, memory limits, and entry integrity.
"""

import time
from graph_storage.cache.cache_entry import CacheEntry
from graph_storage.exceptions import GraphStorageError


class CacheValidator:
    """Validator enforcing cache entry constraints."""

    @classmethod
    def validate_entry(cls, entry: CacheEntry) -> None:
        """Validate required fields."""
        if not entry.cache_key:
            raise GraphStorageError("Cache entry key cannot be empty")
        if entry.value is None:
            raise GraphStorageError("Cache entry payload value cannot be None")

    @classmethod
    def is_expired(cls, entry: CacheEntry, current_time: float = 0.0) -> bool:
        """Check if an entry is expired based on TTL and expiration_time."""
        now = current_time or time.time()
        if entry.expiration_time > 0 and now > entry.expiration_time:
            return True
        return False

    @classmethod
    def validate_memory_limits(cls, size_bytes: int, limit_bytes: int) -> None:
        """Verify that single entry size does not exceed overall cache limit."""
        if size_bytes > limit_bytes:
            raise GraphStorageError(
                f"Single entry size ({size_bytes} bytes) exceeds maximum cache memory limit ({limit_bytes} bytes)"
            )
