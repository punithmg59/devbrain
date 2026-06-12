"""Centrality scoring from precomputed graph metrics — deterministic."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.blast_radius import ImpactMetric


class CentralityService:
    """Compute 0–100 centrality from degrees, workflows, services, critical paths."""

    async def get_node_score(
        self, repo_id: UUID, node_id: UUID, db: AsyncSession
    ) -> float | None:
        row = await db.execute(
            select(ImpactMetric.centrality_score).where(
                ImpactMetric.repo_id == repo_id,
                ImpactMetric.node_id == node_id,
            )
        )
        val = row.scalar_one_or_none()
        return float(val) if val is not None else None

    async def load_scores_for_nodes(
        self, repo_id: UUID, node_ids: list[str], db: AsyncSession
    ) -> dict[str, float]:
        if not node_ids:
            return {}
        uuids = [UUID(n) for n in node_ids]
        rows = (
            await db.execute(
                select(ImpactMetric.node_id, ImpactMetric.centrality_score).where(
                    ImpactMetric.repo_id == repo_id,
                    ImpactMetric.node_id.in_(uuids),
                )
            )
        ).all()
        return {str(r[0]): float(r[1]) for r in rows}

    def compute_score_from_counts(
        self,
        *,
        in_degree: int,
        out_degree: int,
        workflow_count: int,
        service_count: int,
        critical_path_count: int,
        max_in: int,
        max_out: int,
    ) -> float:
        """Deterministic 0–100 score from normalized metrics."""
        in_norm = in_degree / max(max_in, 1)
        out_norm = out_degree / max(max_out, 1)
        degree_score = min(1.0, (in_norm * 0.55 + out_norm * 0.45))
        wf_score = min(1.0, workflow_count / 3.0)
        svc_score = min(1.0, service_count / 2.0)
        cp_score = min(1.0, critical_path_count / 2.0)
        raw = (
            degree_score * 0.40
            + wf_score * 0.20
            + svc_score * 0.15
            + cp_score * 0.25
        )
        return round(min(100.0, max(0.0, raw * 100)), 2)

    async def repo_max_degrees(self, repo_id: UUID, db: AsyncSession) -> tuple[int, int]:
        row = (
            await db.execute(
                text("""
                    SELECT COALESCE(MAX(in_degree), 1), COALESCE(MAX(out_degree), 1)
                    FROM impact_metrics WHERE repo_id = :repo_id
                """),
                {"repo_id": str(repo_id)},
            )
        ).one()
        return int(row[0]), int(row[1])
