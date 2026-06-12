"""Workflow-to-workflow relationships from graph evidence."""

from __future__ import annotations

from collections import defaultdict
from uuid import UUID

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.workflow import Workflow, WorkflowNode


# Deterministic product flow order when graph edges are weak
DEFAULT_WORKFLOW_CHAIN: tuple[tuple[str, str], ...] = (
    ("GitHub Authentication", "Session Management"),
    ("Session Management", "Repository Connection"),
    ("Repository Connection", "Repository Analysis"),
    ("Repository Analysis", "Impact Radar"),
    ("Repository Analysis", "Code Analysis Pipeline"),
    ("Session Management", "Dashboard Experience"),
    ("Dashboard Experience", "Public API Surface"),
)


class WorkflowGraphService:
    async def related_workflow_names(
        self,
        workflow: Workflow,
        repo_id: UUID,
        db: AsyncSession,
    ) -> list[str]:
        """Workflows linked by shared nodes or directed node edges."""
        wf_by_node: dict[str, set[str]] = defaultdict(set)
        result = await db.execute(
            select(Workflow)
            .where(Workflow.repo_id == repo_id)
            .options(
                selectinload(Workflow.nodes),
            )
        )
        all_wfs = result.scalars().all()
        name_by_id = {str(w.id): w.name for w in all_wfs}
        for wf in all_wfs:
            for wn in wf.nodes:
                wf_by_node[str(wn.node_id)].add(wf.name)

        node_ids = [str(wn.node_id) for wn in workflow.nodes]
        if not node_ids:
            return self._default_related(workflow.name)

        edge_rows = (
            await db.execute(
                text("""
                    SELECT e.from_node_id, e.to_node_id
                    FROM edges e
                    WHERE e.repo_id = :repo_id
                      AND (
                        e.from_node_id = ANY(:ids)
                        OR e.to_node_id = ANY(:ids)
                      )
                    LIMIT 500
                """),
                {"repo_id": str(repo_id), "ids": [UUID(n) for n in node_ids]},
            )
        ).mappings()

        related: set[str] = set()
        for row in edge_rows:
            fid, tid = str(row["from_node_id"]), str(row["to_node_id"])
            for nid in (fid, tid):
                for other in wf_by_node.get(nid, ()):
                    if other != workflow.name:
                        related.add(other)

        if not related:
            related.update(self._default_related(workflow.name))
        return sorted(related)[:8]

    def _default_related(self, workflow_name: str) -> set[str]:
        out: set[str] = set()
        for src, dst in DEFAULT_WORKFLOW_CHAIN:
            if src == workflow_name:
                out.add(dst)
            if dst == workflow_name:
                out.add(src)
        return out

    def workflow_chain_for_names(self, names: list[str]) -> list[tuple[str, str]]:
        name_set = set(names)
        return [(a, b) for a, b in DEFAULT_WORKFLOW_CHAIN if a in name_set and b in name_set]
