import hashlib
import logging

from app.schemas.impact import ImpactResult
from app.utils.redis_client import get_redis, is_redis_available

logger = logging.getLogger(__name__)

CACHE_TTL_SECONDS = 300


def build_cache_key(
    repo_id: str,
    query: str,
    max_depth: int,
    direction: str,
) -> str:
    """Key format: impact:{repo_id}:{hash(query+params)}."""
    raw = f"{query.strip().lower()}|{max_depth}|{direction}"
    digest = hashlib.sha256(raw.encode()).hexdigest()[:16]
    return f"impact:{repo_id}:{digest}"


async def get_cached_impact(key: str) -> ImpactResult | None:
    if not is_redis_available():
        return None
    try:
        redis = get_redis()
        data = await redis.get(key)
        if not data:
            return None
        return ImpactResult.model_validate_json(data)
    except Exception as e:
        logger.debug("Impact cache read skipped: %s", e)
        return None


async def set_cached_impact(key: str, result: ImpactResult) -> None:
    if not is_redis_available():
        return
    try:
        redis = get_redis()
        await redis.setex(key, CACHE_TTL_SECONDS, result.model_dump_json())
    except Exception as e:
        logger.debug("Impact cache write skipped: %s", e)
