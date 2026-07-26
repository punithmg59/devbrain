"""
Cache event model interfaces.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class CacheHitEvent:
    cache_key: str
    timestamp_epoch_sec: float


@dataclass(frozen=True)
class CacheMissEvent:
    cache_key: str
    timestamp_epoch_sec: float


@dataclass(frozen=True)
class CacheEvictedEvent:
    cache_key: str
    reason: str
    timestamp_epoch_sec: float


@dataclass(frozen=True)
class CacheExpiredEvent:
    cache_key: str
    timestamp_epoch_sec: float


@dataclass(frozen=True)
class CachePrefetchedEvent:
    cache_key: str
    timestamp_epoch_sec: float
