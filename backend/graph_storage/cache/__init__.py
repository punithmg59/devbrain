"""
Cache package for Graph Storage memory management and caching.
"""

from graph_storage.cache.cache_builder import CacheBuilder
from graph_storage.cache.cache_entry import CacheEntry
from graph_storage.cache.cache_events import (
    CacheEvictedEvent,
    CacheExpiredEvent,
    CacheHitEvent,
    CacheMissEvent,
    CachePrefetchedEvent,
)
from graph_storage.cache.cache_index import CacheIndex
from graph_storage.cache.cache_manager import CacheManager
from graph_storage.cache.cache_metrics import CacheMetrics
from graph_storage.cache.cache_policy import CachePolicy
from graph_storage.cache.cache_repository import (
    CacheRepository,
    InMemoryCacheRepository,
)
from graph_storage.cache.cache_validator import CacheValidator
from graph_storage.cache.eviction_strategy import (
    EvictionStrategy,
    LRUEvictionStrategy,
)
from graph_storage.cache.memory_budget import MemoryBudget
from graph_storage.cache.prefetch_planner import (
    PrefetchPlanner,
    SimpleSequentialPrefetch,
)
from graph_storage.cache.read_ahead_strategy import (
    ReadAheadStrategy,
    SequentialReadAhead,
)
from graph_storage.cache.segment_cache import SegmentCache

__all__ = [
    "CacheEntry",
    "CachePolicy",
    "CacheMetrics",
    "CacheHitEvent",
    "CacheMissEvent",
    "CacheEvictedEvent",
    "CacheExpiredEvent",
    "CachePrefetchedEvent",
    "CacheRepository",
    "InMemoryCacheRepository",
    "CacheIndex",
    "EvictionStrategy",
    "LRUEvictionStrategy",
    "MemoryBudget",
    "PrefetchPlanner",
    "SimpleSequentialPrefetch",
    "ReadAheadStrategy",
    "SequentialReadAhead",
    "CacheValidator",
    "CacheBuilder",
    "CacheManager",
    "SegmentCache",
]
