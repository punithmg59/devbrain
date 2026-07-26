"""
CacheMetrics model definition.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class CacheMetrics:
    """Immutable telemetry metrics for the cache subsystem."""

    hit_rate: float
    miss_rate: float
    hit_count: int
    miss_count: int
    eviction_count: int
    memory_usage_bytes: int
    average_lookup_time_ms: float
    average_insert_time_ms: float
    entry_count: int
