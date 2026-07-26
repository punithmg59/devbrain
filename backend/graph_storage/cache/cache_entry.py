"""
CacheEntry model definition.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class CacheEntry:
    """Immutable representation of a cached storage artifact entry."""

    cache_key: str
    value: bytes
    created_time: float
    last_access_time: float
    access_count: int
    size_bytes: int
    priority: int = 1
    ttl_seconds: float = 3600.0
    expiration_time: float = 0.0
