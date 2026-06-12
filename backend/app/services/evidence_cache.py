"""Evidence cache storage for repository-level evidence."""

import logging
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import EvidenceCache

logger = logging.getLogger(__name__)


class EvidenceCacheService:
    async def get_cached_evidence(
        self,
        repo_id: str,
        cache_key: str,
        db: AsyncSession,
    ) -> dict | None:
        result = await db.execute(
            select(EvidenceCache).where(
                EvidenceCache.repo_id == repo_id,
                EvidenceCache.cache_key == cache_key,
            )
        )
        row = result.scalar_one_or_none()
        if not row:
            return None
        return row.result

    async def set_cached_evidence(
        self,
        repo_id: str,
        cache_key: str,
        query: str,
        result_data: dict,
        db: AsyncSession,
    ) -> None:
        existing = await db.execute(
            select(EvidenceCache).where(
                EvidenceCache.repo_id == repo_id,
                EvidenceCache.cache_key == cache_key,
            )
        )
        cache_row = existing.scalar_one_or_none()
        if cache_row:
            cache_row.query = query
            cache_row.result = result_data
        else:
            db.add(
                EvidenceCache(
                    repo_id=repo_id,
                    cache_key=cache_key,
                    query=query,
                    result=result_data,
                )
            )
