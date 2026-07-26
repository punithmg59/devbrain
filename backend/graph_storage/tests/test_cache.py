"""
Unit tests for Caching & Memory Management Subsystem (Step 4.8).
"""

import time
import unittest
from graph_storage.cache import (
    CacheBuilder,
    CacheEntry,
    CacheIndex,
    CacheManager,
    CacheMetrics,
    CachePolicy,
    CacheValidator,
    InMemoryCacheRepository,
    LRUEvictionStrategy,
    MemoryBudget,
    SequentialReadAhead,
    SimpleSequentialPrefetch,
)
from graph_storage.exceptions import GraphStorageError


class TestCacheBuilderAndValidator(unittest.TestCase):
    """Test suite for CacheBuilder, MemoryBudget, and CacheValidator."""

    def test_cache_builder(self):
        builder = (
            CacheBuilder()
            .set_cache_key("key_1")
            .set_value(b"hello world")
            .set_priority(2)
            .set_ttl_seconds(100.0)
        )
        entry = builder.build()

        self.assertEqual(entry.cache_key, "key_1")
        self.assertEqual(entry.value, b"hello world")
        self.assertEqual(entry.size_bytes, 11)
        self.assertEqual(entry.priority, 2)

    def test_memory_budget(self):
        budget = MemoryBudget(limit_bytes=100)
        self.assertTrue(budget.can_allocate(50))
        self.assertTrue(budget.allocate(50))
        self.assertEqual(budget.used, 50)
        self.assertEqual(budget.headroom, 50)

        self.assertFalse(budget.allocate(60))
        budget.release(20)
        self.assertEqual(budget.used, 30)

    def test_cache_validator(self):
        entry = CacheBuilder().set_cache_key("k").set_value(b"val").set_ttl_seconds(0.1).build()
        CacheValidator.validate_entry(entry)
        self.assertFalse(CacheValidator.is_expired(entry))

        # Simulate expiration
        future_time = time.time() + 10.0
        self.assertTrue(CacheValidator.is_expired(entry, current_time=future_time))


class TestCacheManagerAndEviction(unittest.TestCase):
    """Test suite for CacheManager, Eviction, and Prefetch."""

    def test_cache_manager_put_and_get(self):
        policy = CachePolicy(maximum_memory_bytes=1000)
        manager = CacheManager(policy=policy)

        manager.put("seg_01", b"payload 1")
        val = manager.get("seg_01")
        self.assertEqual(val, b"payload 1")

        stats = manager.statistics()
        self.assertEqual(stats.hit_count, 1)
        self.assertEqual(stats.miss_count, 0)

    def test_cache_eviction_on_memory_limit(self):
        # Small memory budget (20 bytes max)
        policy = CachePolicy(maximum_memory_bytes=20)
        manager = CacheManager(policy=policy)

        manager.put("k1", b"1234567890")  # 10 bytes
        manager.put("k2", b"1234567890")  # 10 bytes (20 total, full)

        # Adding k3 (10 bytes) forces eviction of LRU entry (k1)
        manager.put("k3", b"1234567890")

        self.assertIsNone(manager.get("k1"))
        self.assertEqual(manager.get("k2"), b"1234567890")
        self.assertEqual(manager.get("k3"), b"1234567890")

        stats = manager.statistics()
        self.assertGreaterEqual(stats.eviction_count, 1)

    def test_prefetch_and_read_ahead(self):
        prefetcher = SimpleSequentialPrefetch()
        predicted = prefetcher.predict_prefetch("seg_001")
        self.assertEqual(predicted, ["seg_002"])

        read_ahead = SequentialReadAhead(count=2)
        ahead = read_ahead.plan_read_ahead("seg_001")
        self.assertEqual(ahead, ["seg_002", "seg_003"])


if __name__ == "__main__":
    unittest.main()
