"""Critical path definitions and impact detection — deterministic."""

from __future__ import annotations

import logging
from uuid import UUID

from sqlalchemy import delete, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.blast_radius import CriticalPath
from app.models.workflow import Workflow

logger = logging.getLogger(__name__)

# Seed definitions: path name -> ordered node name patterns
CRITICAL_PATH_SEEDS: tuple[dict, ...] = (
    {
        "name": "GitHub Login Path",
        "description": "OAuth callback through session creation.",
        "criticality": "high",
        "workflow_name": "GitHub Authentication",
        "node_names": (
            "github_callback",
            "save_github_token",
            "create_session_token",
        ),
    },
    {
        "name": "Repository Onboarding Path",
        "description": "Connect repository and trigger analysis.",
        "criticality": "high",
        "workflow_name": "Repository Connection",
        "node_names": ("connect_repo", "fetch_github_repos", "analyze_repo"),
    },
    {
        "name": "Analysis Path",
        "description": "Repository parsing into knowledge graph.",
        "criticality": "medium",
        "workflow_name": "Repository Analysis",
        "node_names": ("analyze_repo", "run_repo_analysis"),
    },
    {
        "name": "API Request Path",
        "description": "Authenticated API request handling.",
        "criticality": "medium",
        "workflow_name": "Public API Surface",
        "node_names": ("get_current_user",),
    },
)


class CriticalPathService:
    async def seed_for_repo(self, repo_id: UUID, db: AsyncSession) -> int:
        await db.execute(delete(CriticalPath).where(CriticalPath.repo_id == repo_id))

        wf_rows = (
            await db.execute(
                select(Workflow).where(Workflow.repo_id == repo_id)
            )
        ).scalars().all()
        wf_by_name = {w.name: w for w in wf_rows}

        node_rows = (
            await db.execute(
                text("""
                    SELECT id, name FROM nodes WHERE repo_id = :repo_id
                """),
                {"repo_id": str(repo_id)},
            )
        ).mappings()
        nodes_by_name: dict[str, str] = {}
        for r in node_rows:
            nodes_by_name[r["name"].lower()] = str(r["id"])

        count = 0
        for seed in CRITICAL_PATH_SEEDS:
            path_node_refs: list[dict] = []
            for nname in seed["node_names"]:
                nid = nodes_by_name.get(nname.lower())
                if nid:
                    path_node_refs.append({"node_id": nid, "name": nname})

            wf = wf_by_name.get(seed.get("workflow_name", ""))
            db.add(
                CriticalPath(
                    repo_id=repo_id,
                    name=seed["name"],
                    description=seed["description"],
                    criticality=seed["criticality"],
                    workflow_id=wf.id if wf else None,
                    path_nodes=path_node_refs,
                )
            )
            count += 1
        await db.flush()
        return count

    async def list_paths(self, repo_id: UUID, db: AsyncSession) -> list[CriticalPath]:
        result = await db.execute(
            select(CriticalPath).where(CriticalPath.repo_id == repo_id).order_by(CriticalPath.name)
        )
        return list(result.scalars().all())

    def paths_impacted(
        self,
        paths: list[CriticalPath],
        impacted_node_ids: set[str],
        source_node_id: str | None,
    ) -> list[dict]:
        """Return critical paths touched by blast radius."""
        hit_ids = set(impacted_node_ids)
        if source_node_id:
            hit_ids.add(source_node_id)
        out: list[dict] = []
        for path in paths:
            node_refs = path.path_nodes or []
            path_ids = {ref.get("node_id") for ref in node_refs if ref.get("node_id")}
            overlap = path_ids & hit_ids
            if overlap:
                out.append(
                    {
                        "id": str(path.id),
                        "name": path.name,
                        "criticality": path.criticality,
                        "description": path.description,
                        "impacted_node_names": [
                            ref.get("name")
                            for ref in node_refs
                            if ref.get("node_id") in overlap
                        ],
                    }
                )
        return out
