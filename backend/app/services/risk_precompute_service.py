"""Background precomputation for explainable risk profiles."""

from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

from sqlalchemy import delete, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import RiskBreakdown, RiskHistory, RiskProfile
from app.services.risk_engine_v2 import ExplainableRiskEngine

logger = logging.getLogger(__name__)


class RiskPrecomputeService:
    def __init__(self) -> None:
        self.engine = ExplainableRiskEngine()

    async def recompute_for_repo(self, repo_id: UUID, db: AsyncSession) -> dict[str, int]:
        existing_profiles = await self._load_existing_profiles(repo_id, db)
        await db.execute(delete(RiskBreakdown).where(RiskBreakdown.repo_id == repo_id))

        result = await db.execute(
            text(
                """
                SELECT im.node_id::text AS node_id,
                       n.id AS node_uuid,
                       n.name,
                       im.dependency_count,
                       im.workflow_count,
                       im.service_count,
                       im.api_count,
                       im.journey_count,
                       im.centrality_score,
                       im.critical_path_count
                FROM impact_metrics im
                JOIN nodes n ON n.id = im.node_id
                WHERE im.repo_id = :repo_id
                """
            ),
            {"repo_id": str(repo_id)},
        )
        metric_rows = result.mappings().all()

        profile_count = 0
        breakdown_count = 0
        history_count = 0
        for row in metric_rows:
            profile = self.engine.compute_profile_from_metrics(
                row,
                entity_type="node",
                entity_id=row["node_uuid"],
                repo_id=str(repo_id),
            )
            await self._persist_profile(profile, existing_profiles, db)
            profile_count += 1
            breakdown_count += len(profile["risk_factors"])
            if profile["changed"]:
                history_count += 1

        repo_profile = self.engine.compute_repo_profile_from_repo_metrics(
            repo_id=str(repo_id),
            metric_rows=metric_rows,
        )
        if repo_profile:
            await self._persist_profile(repo_profile, existing_profiles, db)
            profile_count += 1
            breakdown_count += len(repo_profile["risk_factors"])
            if repo_profile["changed"]:
                history_count += 1

        await db.flush()
        logger.info(
            "Recomputed risk profiles=%d breakdowns=%d history=%d for repo %s",
            profile_count,
            breakdown_count,
            history_count,
            repo_id,
        )
        return {
            "profiles": profile_count,
            "breakdowns": breakdown_count,
            "history_records": history_count,
        }

    async def _load_existing_profiles(self, repo_id: UUID, db: AsyncSession) -> dict[tuple[str, str], dict[str, Any]]:
        result = await db.execute(
            select(RiskProfile).where(RiskProfile.repo_id == repo_id)
        )
        return {
            (row.entity_type, str(row.entity_id)): {
                "id": row.id,
                "risk_score": float(row.risk_score),
            }
            for row in result.scalars().all()
        }

    async def _persist_profile(
        self,
        profile: dict[str, Any],
        existing_profiles: dict[tuple[str, str], dict[str, Any]],
        db: AsyncSession,
    ) -> None:
        key = (profile["entity_type"], profile["entity_id"])
        previous = existing_profiles.get(key)
        if previous:
            if float(previous["risk_score"]) != profile["risk_score"]:
                db.add(
                    RiskHistory(
                        repo_id=UUID(profile["repo_id"]),
                        entity_id=UUID(profile["entity_id"]),
                        previous_score=previous["risk_score"],
                        new_score=profile["risk_score"],
                        change_reason=profile["change_reason"],
                    )
                )
            await db.execute(
                text(
                    """
                    UPDATE risk_profiles
                    SET risk_score = :risk_score,
                        risk_category = :risk_category,
                        risk_factors = :risk_factors,
                        confidence = :confidence,
                        updated_at = now()
                    WHERE id = :id
                    """
                ),
                {
                    "risk_score": profile["risk_score"],
                    "risk_category": profile["risk_category"],
                    "risk_factors": profile["risk_factors"],
                    "confidence": profile["confidence"],
                    "id": str(previous["id"]),
                },
            )
        else:
            db.add(
                RiskProfile(
                    repo_id=UUID(profile["repo_id"]),
                    entity_type=profile["entity_type"],
                    entity_id=UUID(profile["entity_id"]),
                    risk_score=profile["risk_score"],
                    risk_category=profile["risk_category"],
                    risk_factors=profile["risk_factors"],
                    confidence=profile["confidence"],
                )
            )

        for factor in profile["risk_factors"]:
            db.add(
                RiskBreakdown(
                    repo_id=UUID(profile["repo_id"]),
                    entity_id=UUID(profile["entity_id"]),
                    factor_name=factor["factor_name"],
                    factor_score=factor["factor_score"],
                    weight=factor["weight"],
                    evidence=factor["evidence"],
                )
            )

    def _aggregate_metrics(self, metric_rows: list[dict[str, Any]]) -> dict[str, float]:
        totals = {
            "dependency_count": 0,
            "workflow_count": 0,
            "service_count": 0,
            "api_count": 0,
            "journey_count": 0,
            "centrality_score": 0.0,
            "critical_path_count": 0,
            "rows": 0,
        }
        for row in metric_rows:
            totals["dependency_count"] += int(row["dependency_count"])
            totals["workflow_count"] += int(row["workflow_count"])
            totals["service_count"] += int(row["service_count"])
            totals["api_count"] += int(row["api_count"])
            totals["journey_count"] += int(row["journey_count"])
            totals["centrality_score"] += float(row["centrality_score"] or 0.0)
            totals["critical_path_count"] += int(row["critical_path_count"])
            totals["rows"] += 1
        return totals
