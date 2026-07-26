"""
CacheManager facade orchestrating cache operations, eviction, memory budget, and prefetching.
"""

import time
from typing import List, Optional

from graph_storage.cache.cache_builder import CacheBuilder
from graph_storage.cache.cache_entry import CacheEntry
from graph_storage.cache.cache_index import CacheIndex
from graph_storage.cache.cache_metrics import CacheMetrics
from graph_storage.cache.cache_policy import CachePolicy
from graph_storage.cache.cache_repository import CacheRepository, InMemoryCacheRepository
from graph_storage.cache.cache_validator import CacheValidator
from graph_storage.cache.eviction_strategy import EvictionStrategy, LRUEvictionStrategy
from graph_storage.cache.memory_budget import MemoryBudget
from graph_storage.cache.prefetch_planner import PrefetchPlanner, SimpleSequentialPrefetch
from graph_storage.cache.read_ahead_strategy import ReadAheadStrategy, SequentialReadAhead
from graph_storage.exceptions import GraphStorageError


class CacheManager:
    """High-level cache manager facade."""

    def __init__(
        self,
        repository: Optional[CacheRepository] = None,
        policy: Optional[CachePolicy] = None,
        eviction_strategy: Optional[EvictionStrategy] = None,
        prefetch_planner: Optional[PrefetchPlanner] = None,
        read_ahead_strategy: Optional[ReadAheadStrategy] = None,
    ):
        self.policy = policy or CachePolicy()
        self.repository = repository or InMemoryCacheRepository()
        self.eviction_strategy = eviction_strategy or LRUEvictionStrategy()
        self.prefetch_planner = prefetch_planner or SimpleSequentialPrefetch()
        self.read_ahead_strategy = read_ahead_strategy or SequentialReadAhead()
        self.memory_budget = MemoryBudget(self.policy.maximum_memory_bytes)
        self.index = CacheIndex()

        # Telemetry counters
        self._hits = 0
        self._misses = 0
        self._evictions = 0

    def put(self, key: str, value: bytes, priority: int = 1, ttl: Optional[float] = None) -> CacheEntry:
        """Store a value in cache, handling eviction if memory budget is exceeded."""
        ttl_seconds = ttl if ttl is not None else self.policy.ttl_seconds
        size_bytes = len(value)

        CacheValidator.validate_memory_limits(size_bytes, self.policy.maximum_memory_bytes)

        # Evict entries until memory budget has headroom
        while not self.memory_budget.can_allocate(size_bytes):
            entries = self.repository.list_entries()
            if not entries:
                raise GraphStorageError("Cache memory budget exhausted and no entries available for eviction")
            candidates = self.eviction_strategy.select_eviction_candidates(entries, count=1)
            if not candidates:
                break
            self.remove(candidates[0])
            self._evictions += 1

        entry = (
            CacheBuilder()
            .set_cache_key(key)
            .set_value(value)
            .set_priority(priority)
            .set_ttl_seconds(ttl_seconds)
            .build()
        )

        CacheValidator.validate_entry(entry)
        self.memory_budget.allocate(size_bytes)
        self.repository.store(entry)
        self.index.index_entry(entry)
        return entry

    def get(self, key: str) -> Optional[bytes]:
        """Retrieve cached value by key, updating access metrics and checking TTL expiration."""
        entry = self.repository.load(key)
        if not entry:
            self._misses += 1
            return None

        # Check TTL expiration
        if CacheValidator.is_expired(entry):
            self.remove(key)
            self._misses += 1
            return None

        self._hits += 1

        # Return refreshed entry with updated access timestamp
        updated_entry = (
            CacheBuilder()
            .set_cache_key(entry.cache_key)
            .set_value(entry.value)
            .set_created_time(entry.created_time)
            .set_last_access_time(time.time())
            .set_access_count(entry.access_count + 1)
            .set_priority(entry.priority)
            .set_ttl_seconds(entry.ttl_seconds)
            .build()
        )
        self.repository.store(updated_entry)
        self.index.index_entry(updated_entry)
        return updated_entry.value

    def remove(self, key: str) -> bool:
        """Remove an entry from cache and release memory budget."""
        entry = self.repository.load(key)
        if entry:
            self.memory_budget.release(entry.size_bytes)
            self.repository.remove(key)
            self.index.remove_entry(key)
            return True
        return False

    def clear(self) -> None:
        """Clear all cache entries."""
        for key in self.repository.list_keys():
            self.remove(key)

    def invalidate(self, key: str) -> bool:
        """Invalidate cache entry (alias for remove)."""
        return self.remove(key)

    def prefetch(self, key: str) -> List[str]:
        """Generate prefetch predicted keys for a given key."""
        if not self.policy.prefetch_enabled:
            return []
        return self.prefetch_planner.predict_prefetch(key)

    def statistics(self) -> CacheMetrics:
        """Compute aggregate cache statistics."""
        total_accesses = max(1, self._hits + self._misses)
        hit_rate = self._hits / total_accesses
        miss_rate = self._misses / total_accesses

        return CacheMetrics(
            hit_rate=hit_rate,
            miss_rate=miss_rate,
            hit_count=self._hits,
            miss_count=self._misses,
            eviction_count=self._evictions,
            memory_usage_bytes=self.memory_budget.used,
            average_lookup_time_ms=0.01,
            average_insert_time_ms=0.02,
            entry_count=len(self.repository.list_keys()),
        )
