"""
tests/test_oauth_state_storage.py

Unit tests for the OAuthStateStorage strategy pattern.

Covers:
  ✓ RedisOAuthStateStorage — save / get / delete lifecycle
  ✓ MemoryOAuthStateStorage — save / get / delete lifecycle
  ✓ TTL expiration (memory)
  ✓ Concurrent access / thread safety (memory)
  ✓ OAuthStateStorageFactory — Redis-present selects Redis
  ✓ OAuthStateStorageFactory — Redis-absent selects Memory
  ✓ Backward compatibility — redis_client.is_redis_available() still works
"""

from __future__ import annotations

import asyncio
import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.utils.oauth_state_storage import (
    MemoryOAuthStateStorage,
    OAuthStateStorageFactory,
    RedisOAuthStateStorage,
    get_oauth_state_storage,
    shutdown_oauth_state_storage,
)


# ─────────────────────────────────────────────────────────────────────────────
# Helpers / fixtures
# ─────────────────────────────────────────────────────────────────────────────


def make_mock_redis() -> MagicMock:
    """Return a MagicMock that mimics the aioredis.Redis async interface."""
    r = MagicMock()
    r.setex = AsyncMock(return_value=True)
    r.get = AsyncMock(return_value="1")
    r.delete = AsyncMock(return_value=1)
    return r


@pytest.fixture(autouse=True)
def reset_singleton() -> None:
    """Reset the singleton before every test so tests are isolated."""
    OAuthStateStorageFactory.reset()
    yield
    OAuthStateStorageFactory.reset()


# ─────────────────────────────────────────────────────────────────────────────
# RedisOAuthStateStorage
# ─────────────────────────────────────────────────────────────────────────────


class TestRedisOAuthStateStorage:
    """Tests for RedisOAuthStateStorage.

    The actual Redis client is mocked so these tests run without a live server.
    """

    def _make_storage(self, mock_redis: MagicMock) -> RedisOAuthStateStorage:
        storage = RedisOAuthStateStorage.__new__(RedisOAuthStateStorage)
        storage._get_redis = lambda: mock_redis
        return storage

    @pytest.mark.asyncio
    async def test_save_state_calls_setex(self) -> None:
        mock_redis = make_mock_redis()
        storage = self._make_storage(mock_redis)

        await storage.save_state("abc123", ttl=300)

        mock_redis.setex.assert_awaited_once_with("oauth_state:abc123", 300, "1")

    @pytest.mark.asyncio
    async def test_save_state_default_ttl(self) -> None:
        mock_redis = make_mock_redis()
        storage = self._make_storage(mock_redis)

        await storage.save_state("tok")

        _, ttl, _ = mock_redis.setex.await_args.args
        assert ttl == 600

    @pytest.mark.asyncio
    async def test_get_state_returns_value_when_present(self) -> None:
        mock_redis = make_mock_redis()
        mock_redis.get = AsyncMock(return_value="1")
        storage = self._make_storage(mock_redis)

        result = await storage.get_state("abc123")

        assert result == "1"
        mock_redis.get.assert_awaited_once_with("oauth_state:abc123")

    @pytest.mark.asyncio
    async def test_get_state_returns_none_when_absent(self) -> None:
        mock_redis = make_mock_redis()
        mock_redis.get = AsyncMock(return_value=None)
        storage = self._make_storage(mock_redis)

        result = await storage.get_state("missing")

        assert result is None

    @pytest.mark.asyncio
    async def test_delete_state_calls_delete(self) -> None:
        mock_redis = make_mock_redis()
        storage = self._make_storage(mock_redis)

        await storage.delete_state("abc123")

        mock_redis.delete.assert_awaited_once_with("oauth_state:abc123")

    @pytest.mark.asyncio
    async def test_full_lifecycle(self) -> None:
        """save → get (found) → delete → get (not found)."""
        store: dict[str, str] = {}

        mock_redis = MagicMock()
        mock_redis.setex = AsyncMock(side_effect=lambda k, _ttl, v: store.__setitem__(k, v))
        mock_redis.get = AsyncMock(side_effect=lambda k: store.get(k))
        mock_redis.delete = AsyncMock(side_effect=lambda k: store.pop(k, None))

        storage = self._make_storage(mock_redis)
        state = "lifecycle_token"

        await storage.save_state(state)
        assert await storage.get_state(state) == "1"

        await storage.delete_state(state)
        assert await storage.get_state(state) is None

    @pytest.mark.asyncio
    async def test_cleanup_is_noop(self) -> None:
        """cleanup() must not raise even if Redis has no special teardown."""
        mock_redis = make_mock_redis()
        storage = self._make_storage(mock_redis)
        await storage.cleanup()  # should not raise


# ─────────────────────────────────────────────────────────────────────────────
# MemoryOAuthStateStorage
# ─────────────────────────────────────────────────────────────────────────────


class TestMemoryOAuthStateStorage:
    @pytest.mark.asyncio
    async def test_save_and_get(self) -> None:
        storage = MemoryOAuthStateStorage()
        await storage.save_state("tok1")
        assert await storage.get_state("tok1") == "1"
        await storage.cleanup()

    @pytest.mark.asyncio
    async def test_get_returns_none_for_unknown_key(self) -> None:
        storage = MemoryOAuthStateStorage()
        assert await storage.get_state("ghost") is None

    @pytest.mark.asyncio
    async def test_delete_removes_state(self) -> None:
        storage = MemoryOAuthStateStorage()
        await storage.save_state("del_me")
        await storage.delete_state("del_me")
        assert await storage.get_state("del_me") is None
        await storage.cleanup()

    @pytest.mark.asyncio
    async def test_delete_nonexistent_is_noop(self) -> None:
        storage = MemoryOAuthStateStorage()
        await storage.delete_state("phantom")  # should not raise

    @pytest.mark.asyncio
    async def test_ttl_expiration(self) -> None:
        """State with TTL=0 is immediately expired on next get."""
        storage = MemoryOAuthStateStorage()
        state = "expire_me"

        # Use a TTL of -1 second → entry is already past its expiry the instant
        # it is stored; get_state should evict and return None.
        async with storage._lock:
            storage._store[state] = ("1", time.monotonic() - 1)

        assert await storage.get_state(state) is None
        await storage.cleanup()

    @pytest.mark.asyncio
    async def test_ttl_not_expired_yet(self) -> None:
        """State with long TTL is still retrievable."""
        storage = MemoryOAuthStateStorage()
        await storage.save_state("valid_tok", ttl=9999)
        assert await storage.get_state("valid_tok") == "1"
        await storage.cleanup()

    @pytest.mark.asyncio
    async def test_cleanup_clears_store_and_cancels_sweep(self) -> None:
        storage = MemoryOAuthStateStorage()
        await storage.save_state("will_be_gone")
        await storage.cleanup()
        # After cleanup the internal store is empty
        assert storage._store == {}
        # Sweep task is cancelled
        if storage._sweep_task:
            assert storage._sweep_task.cancelled() or storage._sweep_task.done()

    @pytest.mark.asyncio
    async def test_thread_safety_concurrent_writes(self) -> None:
        """50 concurrent coroutines each write a unique token; all must be retrievable."""
        storage = MemoryOAuthStateStorage()
        tokens = [f"tok_{i}" for i in range(50)]

        await asyncio.gather(*[storage.save_state(t) for t in tokens])

        results = await asyncio.gather(*[storage.get_state(t) for t in tokens])
        assert all(r == "1" for r in results)
        await storage.cleanup()

    @pytest.mark.asyncio
    async def test_thread_safety_concurrent_delete(self) -> None:
        """Concurrent deletes of the same key must not raise."""
        storage = MemoryOAuthStateStorage()
        await storage.save_state("shared")
        # Fire 20 concurrent deletes of the same state
        await asyncio.gather(*[storage.delete_state("shared") for _ in range(20)])
        assert await storage.get_state("shared") is None
        await storage.cleanup()

    @pytest.mark.asyncio
    async def test_sweep_removes_expired_entries(self) -> None:
        """_expire_all() removes all expired entries from the store."""
        storage = MemoryOAuthStateStorage()

        # Manually inject two entries: one expired, one valid
        now = time.monotonic()
        async with storage._lock:
            storage._store["expired_key"] = ("1", now - 10)
            storage._store["valid_key"] = ("1", now + 9999)

        await storage._expire_all()

        assert "expired_key" not in storage._store
        assert "valid_key" in storage._store
        await storage.cleanup()


# ─────────────────────────────────────────────────────────────────────────────
# OAuthStateStorageFactory
# ─────────────────────────────────────────────────────────────────────────────


class TestOAuthStateStorageFactory:
    def test_returns_redis_when_redis_available(self) -> None:
        with patch("app.utils.redis_client.is_redis_available", return_value=True):
            storage = OAuthStateStorageFactory.create()
            assert isinstance(storage, RedisOAuthStateStorage)

    def test_returns_memory_when_redis_unavailable(self) -> None:
        with patch("app.utils.redis_client.is_redis_available", return_value=False):
            storage = OAuthStateStorageFactory.create()
            assert isinstance(storage, MemoryOAuthStateStorage)

    def test_never_raises_regardless_of_redis_state(self) -> None:
        for available in (True, False):
            OAuthStateStorageFactory.reset()
            with patch("app.utils.redis_client.is_redis_available", return_value=available):
                if available:
                    with patch(
                        "app.utils.oauth_state_storage.RedisOAuthStateStorage.__init__",
                        return_value=None,
                    ):
                        _ = OAuthStateStorageFactory.create()
                else:
                    _ = OAuthStateStorageFactory.create()


# ─────────────────────────────────────────────────────────────────────────────
# OAuth State Lifecycle (integration-style, memory backend)
# ─────────────────────────────────────────────────────────────────────────────


class TestOAuthStateLifecycle:
    """End-to-end lifecycle tests using MemoryOAuthStateStorage as backend."""

    @pytest.mark.asyncio
    async def test_login_and_callback_lifecycle(self) -> None:
        """Simulate the full OAuth flow: generate → save → validate → delete."""
        import secrets

        storage = MemoryOAuthStateStorage()

        # Step 1: /api/auth/github generates and stores a state
        state = secrets.token_hex(16)
        await storage.save_state(state, ttl=600)

        # Step 2: /api/auth/github/callback validates the state
        stored = await storage.get_state(state)
        assert stored is not None, "State must exist after save"

        # Step 3: callback deletes the state (one-time use)
        await storage.delete_state(state)

        # Step 4: replay attack — state must be gone
        replay = await storage.get_state(state)
        assert replay is None, "State must not be reusable after deletion"

        await storage.cleanup()

    @pytest.mark.asyncio
    async def test_expired_state_rejected_in_callback(self) -> None:
        """Expired states must be rejected just like missing ones."""
        storage = MemoryOAuthStateStorage()
        state = "expired_oauth_state"

        async with storage._lock:
            storage._store[state] = ("1", time.monotonic() - 1)  # already expired

        result = await storage.get_state(state)
        assert result is None, "Expired state must be rejected"
        await storage.cleanup()

    @pytest.mark.asyncio
    async def test_invalid_state_rejected(self) -> None:
        """A state that was never saved is rejected."""
        storage = MemoryOAuthStateStorage()
        result = await storage.get_state("never_saved_state")
        assert result is None


# ─────────────────────────────────────────────────────────────────────────────
# Backward compatibility
# ─────────────────────────────────────────────────────────────────────────────


class TestBackwardCompatibility:
    """redis_client module-level helpers must continue to work unchanged."""

    def test_is_redis_available_returns_bool(self) -> None:
        from app.utils.redis_client import is_redis_available

        result = is_redis_available()
        assert isinstance(result, bool)

    def test_get_redis_raises_when_uninitialized(self) -> None:
        """get_redis() must raise RuntimeError if not initialized — contract preserved."""
        import app.utils.redis_client as rc

        original = rc._redis_client
        rc._redis_client = None
        try:
            with pytest.raises(RuntimeError, match="not initialized"):
                rc.get_redis()
        finally:
            rc._redis_client = original


# ─────────────────────────────────────────────────────────────────────────────
# Singleton Behavior
# ─────────────────────────────────────────────────────────────────────────────


class TestSingleton:
    def test_same_instance_returned_on_repeated_calls(self) -> None:
        """Factory must return the identical object on every call."""
        with patch("app.utils.redis_client.is_redis_available", return_value=False):
            a = OAuthStateStorageFactory.create()
            b = OAuthStateStorageFactory.create()
            c = OAuthStateStorageFactory.create()
        assert a is b is c

    def test_memory_state_persists_across_factory_calls(self) -> None:
        """State written via one create() call is visible via the next."""
        with patch("app.utils.redis_client.is_redis_available", return_value=False):
            s1 = OAuthStateStorageFactory.create()
            s2 = OAuthStateStorageFactory.create()
        # They must be the same object — no need to await, just confirm identity
        assert s1 is s2

    def test_reset_clears_singleton(self) -> None:
        """reset() must allow the next create() to build a fresh instance."""
        with patch("app.utils.redis_client.is_redis_available", return_value=False):
            first = OAuthStateStorageFactory.create()
        OAuthStateStorageFactory.reset()
        with patch("app.utils.redis_client.is_redis_available", return_value=False):
            second = OAuthStateStorageFactory.create()
        assert first is not second

    def test_thread_safe_creation(self) -> None:
        """Concurrent create() calls from multiple threads produce one instance."""
        import threading

        instances: list = []
        errors: list = []

        def worker() -> None:
            try:
                with patch("app.utils.redis_client.is_redis_available", return_value=False):
                    instances.append(OAuthStateStorageFactory.create())
            except Exception as exc:  # noqa: BLE001
                errors.append(exc)

        threads = [threading.Thread(target=worker) for _ in range(20)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert not errors
        # All threads must have received the same instance
        assert len({id(i) for i in instances}) == 1


# ─────────────────────────────────────────────────────────────────────────────
# FastAPI Dependency Provider
# ─────────────────────────────────────────────────────────────────────────────


class TestGetOAuthStateStorage:
    def test_provider_returns_singleton(self) -> None:
        """get_oauth_state_storage() must delegate to the factory singleton."""
        with patch("app.utils.redis_client.is_redis_available", return_value=False):
            via_factory = OAuthStateStorageFactory.create()
            via_provider = get_oauth_state_storage()
        assert via_factory is via_provider

    def test_provider_returns_oauthstatestorage_instance(self) -> None:
        from app.utils.oauth_state_storage import OAuthStateStorage

        with patch("app.utils.redis_client.is_redis_available", return_value=False):
            storage = get_oauth_state_storage()
        assert isinstance(storage, OAuthStateStorage)


# ─────────────────────────────────────────────────────────────────────────────
# Clean Shutdown
# ─────────────────────────────────────────────────────────────────────────────


class TestShutdown:
    @pytest.mark.asyncio
    async def test_shutdown_cancels_sweep_task(self) -> None:
        """shutdown_oauth_state_storage must cancel the background sweep task."""
        with patch("app.utils.redis_client.is_redis_available", return_value=False):
            storage = OAuthStateStorageFactory.create()
        assert isinstance(storage, MemoryOAuthStateStorage)

        # Trigger sweep task creation
        await storage.save_state("tok")
        assert storage._sweep_task is not None

        # Shutdown via the module-level hook
        await shutdown_oauth_state_storage()

        # Task must be done (cancelled)
        assert storage._sweep_task.done()
        # Store must be empty
        assert storage._store == {}

    @pytest.mark.asyncio
    async def test_shutdown_resets_singleton(self) -> None:
        """After shutdown the singleton slot is cleared."""
        import app.utils.oauth_state_storage as mod

        with patch("app.utils.redis_client.is_redis_available", return_value=False):
            OAuthStateStorageFactory.create()

        await shutdown_oauth_state_storage()
        assert mod._storage_instance is None

    @pytest.mark.asyncio
    async def test_shutdown_idempotent(self) -> None:
        """Calling shutdown twice must not raise."""
        with patch("app.utils.redis_client.is_redis_available", return_value=False):
            OAuthStateStorageFactory.create()
        await shutdown_oauth_state_storage()
        await shutdown_oauth_state_storage()  # second call — must be a no-op

    @pytest.mark.asyncio
    async def test_no_orphan_tasks_after_shutdown(self) -> None:
        """No named oauth_state_sweep tasks should remain after shutdown."""
        with patch("app.utils.redis_client.is_redis_available", return_value=False):
            storage = OAuthStateStorageFactory.create()
        await storage.save_state("tok")  # starts sweep

        await shutdown_oauth_state_storage()

        running = [
            t for t in asyncio.all_tasks()
            if t.get_name() == "oauth_state_sweep" and not t.done()
        ]
        assert running == [], f"Orphan sweep tasks found: {running}"
