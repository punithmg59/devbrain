"""
app/utils/oauth_state_storage.py

OAuthStateStorage — Strategy Pattern implementation.

Architecture:
    OAuthStateStorage (Abstract Interface)
        ├── RedisOAuthStateStorage   — delegates to existing Redis pool
        └── MemoryOAuthStateStorage  — single-process in-memory fallback
    OAuthStateStorageFactory         — singleton, thread-safe, lazy factory
    get_oauth_state_storage()        — FastAPI Depends() provider
    shutdown_oauth_state_storage()   — called by FastAPI shutdown hook

Design Principles Applied:
    - Dependency Inversion  (auth.py depends on abstract interface only)
    - Strategy Pattern      (implementations are interchangeable)
    - Factory Pattern       (creation & lifecycle isolated in factory)
    - Singleton Pattern     (one backend instance for process lifetime)
    - Single Responsibility (each class has one reason to change)
    - Open/Closed           (add new backends without touching auth.py)

Lifecycle:
    FastAPI startup  ──► (lazy; first request triggers creation)
    FastAPI shutdown ──► shutdown_oauth_state_storage() cancels sweep task
"""

from __future__ import annotations

import asyncio
import logging
import threading
import time
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)

_STATE_TTL_SECONDS = 600  # 10 minutes — OAuth standard window


# ─────────────────────────────────────────────────────────────────────────────
# Abstract Interface
# ─────────────────────────────────────────────────────────────────────────────


class OAuthStateStorage(ABC):
    """Abstract interface for OAuth CSRF-state storage.

    All implementations MUST be safe to use from async contexts.
    Each method operates on bare state tokens; implementations are
    responsible for namespacing keys as needed.
    """

    @abstractmethod
    async def save_state(self, state: str, ttl: int = _STATE_TTL_SECONDS) -> None:
        """Persist *state* with a TTL (seconds).  Idempotent."""

    @abstractmethod
    async def get_state(self, state: str) -> str | None:
        """Return the stored value for *state*, or ``None`` if absent/expired."""

    @abstractmethod
    async def delete_state(self, state: str) -> None:
        """Remove *state*.  No-op if it does not exist."""

    @abstractmethod
    async def cleanup(self) -> None:
        """Release resources (connections, memory).  Called on shutdown."""


# ─────────────────────────────────────────────────────────────────────────────
# Redis Implementation
# ─────────────────────────────────────────────────────────────────────────────

_KEY_PREFIX = "oauth_state:"


class RedisOAuthStateStorage(OAuthStateStorage):
    """OAuth state storage backed by the existing Redis connection pool.

    Delegates exclusively to the module-level Redis client managed by
    ``app.utils.redis_client`` — no second connection is created.
    """

    def __init__(self) -> None:
        # Lazy import: module is importable before Redis is initialised.
        from app.utils.redis_client import get_redis

        self._get_redis = get_redis

    @staticmethod
    def _key(state: str) -> str:
        return f"{_KEY_PREFIX}{state}"

    async def save_state(self, state: str, ttl: int = _STATE_TTL_SECONDS) -> None:
        await self._get_redis().setex(self._key(state), ttl, "1")
        logger.debug("[OAuthState/Redis] saved state=%s ttl=%ds", state[:8], ttl)

    async def get_state(self, state: str) -> str | None:
        value = await self._get_redis().get(self._key(state))
        logger.debug("[OAuthState/Redis] get state=%s found=%s", state[:8], value is not None)
        return value

    async def delete_state(self, state: str) -> None:
        await self._get_redis().delete(self._key(state))
        logger.debug("[OAuthState/Redis] deleted state=%s", state[:8])

    async def cleanup(self) -> None:
        # Shared Redis pool is managed by redis_client.close_redis().
        logger.debug("[OAuthState/Redis] cleanup — pool managed externally")


# ─────────────────────────────────────────────────────────────────────────────
# In-Memory Implementation
# ─────────────────────────────────────────────────────────────────────────────


class MemoryOAuthStateStorage(OAuthStateStorage):
    """Thread-safe, TTL-aware in-memory OAuth state store.

    Suitable for single-process deployments (e.g. Railway free tier with no
    Redis add-on).  State is **not** shared across multiple workers/processes.

    Thread Safety:
        Uses ``asyncio.Lock`` so concurrent coroutines cannot race on the
        internal dictionary.  CPython's GIL provides additional safety for
        dict operations from sync threads.

    Expiration:
        Lazy expiration on ``get_state`` + periodic background sweep every
        60 seconds.  The sweep task is started once on first write and is
        cancelled gracefully by ``cleanup()``.
    """

    _SWEEP_INTERVAL = 60  # seconds between background sweeps

    def __init__(self) -> None:
        # {state: (value, expires_at_monotonic)}
        self._store: dict[str, tuple[str, float]] = {}
        self._lock: asyncio.Lock = asyncio.Lock()
        self._sweep_task: asyncio.Task | None = None  # type: ignore[type-arg]

    # ── background sweep ─────────────────────────────────────────────────────

    def _ensure_sweep(self) -> None:
        """Start the background sweep task if not already running.

        Called from within async context (after first save_state).
        Guard handles the edge case where no event loop is running yet
        (e.g. import-time unit tests).
        """
        if self._sweep_task is None or self._sweep_task.done():
            try:
                loop = asyncio.get_running_loop()
                self._sweep_task = loop.create_task(
                    self._sweep_loop(), name="oauth_state_sweep"
                )
                logger.debug("[OAuthState/Memory] background sweep task started")
            except RuntimeError:
                # No running event loop — skip (tests / import time).
                pass

    async def _sweep_loop(self) -> None:
        """Periodically remove expired entries."""
        while True:
            await asyncio.sleep(self._SWEEP_INTERVAL)
            await self._expire_all()

    async def _expire_all(self) -> None:
        now = time.monotonic()
        async with self._lock:
            expired = [k for k, (_, exp) in self._store.items() if now > exp]
            for k in expired:
                del self._store[k]
        if expired:
            logger.debug("[OAuthState/Memory] swept %d expired state(s)", len(expired))

    # ── interface ────────────────────────────────────────────────────────────

    async def save_state(self, state: str, ttl: int = _STATE_TTL_SECONDS) -> None:
        expires_at = time.monotonic() + ttl
        async with self._lock:
            self._store[state] = ("1", expires_at)
        self._ensure_sweep()
        logger.debug("[OAuthState/Memory] saved state=%s ttl=%ds", state[:8], ttl)

    async def get_state(self, state: str) -> str | None:
        async with self._lock:
            entry = self._store.get(state)
            if entry is None:
                logger.debug("[OAuthState/Memory] get state=%s → not found", state[:8])
                return None
            value, expires_at = entry
            if time.monotonic() > expires_at:
                del self._store[state]
                logger.debug("[OAuthState/Memory] get state=%s → expired", state[:8])
                return None
        logger.debug("[OAuthState/Memory] get state=%s → found", state[:8])
        return value

    async def delete_state(self, state: str) -> None:
        async with self._lock:
            self._store.pop(state, None)
        logger.debug("[OAuthState/Memory] deleted state=%s", state[:8])

    async def cleanup(self) -> None:
        """Cancel sweep task and clear store.  Safe to call multiple times."""
        if self._sweep_task and not self._sweep_task.done():
            self._sweep_task.cancel()
            try:
                await self._sweep_task
            except asyncio.CancelledError:
                pass
            logger.debug("[OAuthState/Memory] sweep task cancelled")
        async with self._lock:
            self._store.clear()
        logger.info("[OAuthState/Memory] cleanup complete")


# ─────────────────────────────────────────────────────────────────────────────
# Factory — Singleton, thread-safe, lazy
# ─────────────────────────────────────────────────────────────────────────────

# Module-level singleton + a threading.Lock to guarantee one-time creation
# even if the first two requests arrive simultaneously before the instance
# is assigned.
_storage_instance: OAuthStateStorage | None = None
_storage_lock = threading.Lock()


class OAuthStateStorageFactory:
    """Creates and manages the singleton ``OAuthStateStorage`` instance.

    Selection logic (in priority order):

    1. Redis connected  → ``RedisOAuthStateStorage``
    2. Fallback         → ``MemoryOAuthStateStorage``

    Singleton Guarantee:
        The backend instance is created exactly once per process, protected by
        a ``threading.Lock``.  Subsequent calls to ``create()`` return the same
        object so that ``MemoryOAuthStateStorage`` state survives across
        requests.

    The factory never raises; it always returns a usable implementation.
    """

    @staticmethod
    def create() -> OAuthStateStorage:
        """Return (or lazily create) the process-wide storage singleton."""
        global _storage_instance

        # Fast path — already initialised (no lock needed).
        if _storage_instance is not None:
            return _storage_instance

        # Slow path — first call; use lock to prevent double-creation.
        with _storage_lock:
            if _storage_instance is not None:  # re-check after acquiring lock
                return _storage_instance

            from app.utils.redis_client import is_redis_available

            if is_redis_available():
                logger.info(
                    "[OAuthStateStorageFactory] initialising singleton: RedisOAuthStateStorage"
                )
                _storage_instance = RedisOAuthStateStorage()
            else:
                logger.warning(
                    "[OAuthStateStorageFactory] Redis unavailable — "
                    "initialising singleton: MemoryOAuthStateStorage "
                    "(single-process only; deploy Redis for multi-worker production)"
                )
                _storage_instance = MemoryOAuthStateStorage()

        return _storage_instance

    @staticmethod
    def reset() -> None:
        """Reset the singleton.  FOR TESTING ONLY — never call in production."""
        global _storage_instance
        with _storage_lock:
            _storage_instance = None


# ─────────────────────────────────────────────────────────────────────────────
# FastAPI Dependency Provider
# ─────────────────────────────────────────────────────────────────────────────


def get_oauth_state_storage() -> OAuthStateStorage:
    """FastAPI dependency that resolves to the singleton OAuthStateStorage.

    Usage in routers::

        @router.get("/api/auth/github")
        async def github_login(
            storage: OAuthStateStorage = Depends(get_oauth_state_storage),
        ) -> RedirectResponse:
            ...

    auth.py imports only this function and ``OAuthStateStorage``.
    Construction logic stays entirely inside the factory.
    """
    return OAuthStateStorageFactory.create()


# ─────────────────────────────────────────────────────────────────────────────
# Shutdown hook
# ─────────────────────────────────────────────────────────────────────────────


async def shutdown_oauth_state_storage() -> None:
    """Cleanly shut down the singleton storage backend.

    Call from the FastAPI ``shutdown`` lifecycle event (main.py).

    - Cancels and awaits the MemoryOAuthStateStorage sweep task (if running).
    - Clears in-memory state.
    - Resets the singleton so tests/reloads start fresh.
    """
    global _storage_instance

    with _storage_lock:
        instance = _storage_instance
        _storage_instance = None  # prevent further use immediately

    if instance is not None:
        await instance.cleanup()
        logger.info("[OAuthStateStorage] shutdown complete")
    else:
        logger.debug("[OAuthStateStorage] shutdown — no instance to clean up")
