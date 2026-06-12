"""Precompute impact metrics after repository analysis — batch SQL."""

from __future__ import annotations

import logging
from uuid import UUID

from sqlalchemy import delete, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.blast_radius import ImpactMetric
from app.services.centrality_service import CentralityService

logger = logging.getLogger(__name__)

BATCH_SIZE = 500


class ImpactPrecomputeService:
    def __init__(self) -> None:
        self.centrality = CentralityService()

    async def recompute_for_repo(self, repo_id: UUID, db: AsyncSession) -> int:
        await db.execute(delete(ImpactMetric).where(ImpactMetric.repo_id == repo_id))

        degree_rows = (
            await db.execute(
                text("""
                    SELECT n.id AS node_id,
                           COALESCE(ind.c, 0) AS in_degree,
                           COALESCE(outd.c, 0) AS out_degree
                    FROM nodes n
                    LEFT JOIN (
                        SELECT to_node_id AS nid, COUNT(*) AS c
                        FROM edges WHERE repo_id = :repo_id
                        GROUP BY to_node_id
                    ) ind ON ind.nid = n.id
                    LEFT JOIN (
                        SELECT from_node_id AS nid, COUNT(*) AS c
                        FROM edges WHERE repo_id = :repo_id
                        GROUP BY from_node_id
                    ) outd ON outd.nid = n.id
                    WHERE n.repo_id = :repo_id
                """),
                {"repo_id": str(repo_id)},
            )
        ).mappings().all()

        wf_counts = await self._workflow_counts(repo_id, db)
        svc_counts = await self._service_counts(repo_id, db)
        cp_counts = await self._critical_path_counts(repo_id, db)
        api_flags = await self._api_nodes(repo_id, db)

        max_in = max((int(r["in_degree"]) for r in degree_rows), default=1)
        max_out = max((int(r["out_degree"]) for r in degree_rows), default=1)

        count = 0
        for row in degree_rows:
            nid = str(row["node_id"])
            in_d = int(row["in_degree"])
            out_d = int(row["out_degree"])
            dep_count = in_d + out_d
            wf_c = wf_counts.get(nid, 0)
            svc_c = svc_counts.get(nid, 0)
            cp_c = cp_counts.get(nid, 0)
            journey_c = min(3, wf_c)
            api_c = 1 if nid in api_flags else 0

            centrality = self.centrality.compute_score_from_counts(
                in_degree=in_d,
                out_degree=out_d,
                workflow_count=wf_c,
                service_count=svc_c,
                critical_path_count=cp_c,
                max_in=max_in,
                max_out=max_out,
            )
            blast_hint = min(
                100.0,
                dep_count * 2.0 + wf_c * 5.0 + cp_c * 10.0 + api_c * 8.0,
            )

            db.add(
                ImpactMetric(
                    repo_id=repo_id,
                    node_id=UUID(nid),
                    dependency_count=dep_count,
                    workflow_count=wf_c,
                    service_count=svc_c,
                    api_count=api_c,
                    journey_count=journey_c,
                    centrality_score=centrality,
                    blast_radius_score=blast_hint,
                    in_degree=in_d,
                    out_degree=out_d,
                    critical_path_count=cp_c,
                )
            )
            count += 1
            if count % BATCH_SIZE == 0:
                await db.flush()

        await db.flush()
        logger.info("Precomputed %d impact metrics for repo %s", count, repo_id)
        return count

    async def _workflow_counts(self, repo_id: UUID, db: AsyncSession) -> dict[str, int]:
        rows = (
            await db.execute(
                text("""
                    SELECT wn.node_id::text, COUNT(DISTINCT wn.workflow_id) AS c
                    FROM workflow_nodes wn
                    JOIN workflows w ON w.id = wn.workflow_id
                    WHERE w.repo_id = :repo_id
                    GROUP BY wn.node_id
                """),
                {"repo_id": str(repo_id)},
            )
        ).mappings()
        return {r["node_id"]: int(r["c"]) for r in rows}

    async def _service_counts(self, repo_id: UUID, db: AsyncSession) -> dict[str, int]:
        rows = (
            await db.execute(
                text("""
                    SELECT wn.node_id::text, COUNT(DISTINCT ws.service_name) AS c
                    FROM workflow_nodes wn
                    JOIN workflows w ON w.id = wn.workflow_id
                    JOIN workflow_services ws ON ws.workflow_id = w.id
                    WHERE w.repo_id = :repo_id
                    GROUP BY wn.node_id
                """),
                {"repo_id": str(repo_id)},
            )
        ).mappings()
        return {r["node_id"]: int(r["c"]) for r in rows}

    async def _critical_path_counts(self, repo_id: UUID, db: AsyncSession) -> dict[str, int]:
        rows = (
            await db.execute(
                text("""
                    SELECT cp.path_nodes, cp.id FROM critical_paths cp
                    WHERE cp.repo_id = :repo_id
                """),
                {"repo_id": str(repo_id)},
            )
        ).mappings()
        counts: dict[str, int] = {}
        for row in rows:
            for ref in row["path_nodes"] or []:
                nid = ref.get("node_id")
                if nid:
                    counts[nid] = counts.get(nid, 0) + 1
        return counts

    async def _api_nodes(self, repo_id: UUID, db: AsyncSession) -> set[str]:
        rows = (
            await db.execute(
                text("""
                    SELECT id::text FROM nodes
                    WHERE repo_id = :repo_id
                      AND (node_type = 'api_route' OR route_path IS NOT NULL)
                """),
                {"repo_id": str(repo_id)},
            )
        ).scalars()
        return set(rows.all())
