"""
CachePolicy model definition for cache configuration rules.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class CachePolicy:
    """Immutable policy configuration for memory limits, eviction, and TTL rules."""

    maximum_memory_bytes: int = 104857600  # 100 MB default
    maximum_entries: int = 10000
    ttl_seconds: float = 3600.0
    eviction_policy: str = "LRU"
    prefetch_enabled: bool = True
    read_ahead_enabled: bool = True
