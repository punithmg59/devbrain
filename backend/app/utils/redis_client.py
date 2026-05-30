import logging
import time

import redis.asyncio as aioredis

from app.config import get_settings

logger = logging.getLogger(__name__)

_redis_client: aioredis.Redis | object | None = None


class InMemoryRedis:
    """Development fallback when Redis is unavailable."""

    def __init__(self) -> None:
        self._store: dict[str, tuple[str, float]] = {}

    async def ping(self) -> bool:
        return True

    async def setex(self, key: str, seconds: int, value: str) -> None:
        self._store[key] = (value, time.time() + seconds)

    async def get(self, key: str) -> str | None:
        item = self._store.get(key)
        if item is None:
            return None
        value, expires_at = item
        if time.time() > expires_at:
            self._store.pop(key, None)
            return None
        return value

    async def delete(self, key: str) -> None:
        self._store.pop(key, None)

    async def aclose(self) -> None:
        self._store.clear()


def get_redis() -> aioredis.Redis | InMemoryRedis:
    if _redis_client is None:
        raise RuntimeError("Redis client is not initialized. Call init_redis() first.")
    return _redis_client  # type: ignore[return-value]


def is_redis_available() -> bool:
    return _redis_client is not None


async def init_redis() -> None:
    global _redis_client
    settings = get_settings()
    try:
        client = aioredis.from_url(
            settings.redis_url,
            encoding="utf-8",
            decode_responses=True,
        )
        await client.ping()
        _redis_client = client
        logger.info("Redis connected")
    except Exception as e:
        logger.error("Redis connection failed: %s", e)
        if settings.environment == "development":
            _redis_client = InMemoryRedis()
            logger.warning(
                "Using in-memory store for OAuth state (development only). "
                "Install Redis for production: docker run -d -p 6379:6379 redis:7-alpine"
            )
        else:
            _redis_client = None
            raise


async def close_redis() -> None:
    global _redis_client
    if _redis_client is not None:
        if hasattr(_redis_client, "aclose"):
            await _redis_client.aclose()
        _redis_client = None
        logger.info("Redis connection closed")
