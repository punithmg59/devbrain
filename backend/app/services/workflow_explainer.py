"""Deterministic workflow evidence chains — no LLM."""

from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.workflow import WorkflowEvidenceChain, WorkflowEvidenceStep


class WorkflowExplainer:
    def build_chain(
        self,
        *,
        source_node: dict | None,
        impacted_node_names: list[str],
        workflow_name: str,
        workflow_confidence: float,
    ) -> WorkflowEvidenceChain:
        steps: list[WorkflowEvidenceStep] = []
        if source_node:
            steps.append(
                WorkflowEvidenceStep(
                    label=source_node.get("name", "source"),
                    step_type="node",
                )
            )
        for name in impacted_node_names[:6]:
            if source_node and name == source_node.get("name"):
                continue
            steps.append(WorkflowEvidenceStep(label=name, step_type="node"))

        steps.append(
            WorkflowEvidenceStep(label=workflow_name, step_type="workflow")
        )
        summary = " → ".join(s.label for s in steps)
        return WorkflowEvidenceChain(
            steps=steps,
            confidence=round(workflow_confidence * 100, 1),
            summary=summary,
        )

    async def ordered_nodes_in_workflow(
        self,
        workflow_id: str,
        repo_id: str,
        db: AsyncSession,
        *,
        limit: int = 8,
    ) -> list[str]:
        """Return node names ordered by graph position (sources first)."""
        rows = (
            await db.execute(
                text("""
                    SELECT n.name, n.id,
                           (SELECT COUNT(*) FROM edges e
                            WHERE e.repo_id = :repo_id AND e.to_node_id = n.id) AS in_deg
                    FROM workflow_nodes wn
                    JOIN nodes n ON n.id = wn.node_id
                    WHERE wn.workflow_id = :wf_id
                    ORDER BY in_deg ASC, n.name
                    LIMIT :lim
                """),
                {"repo_id": repo_id, "wf_id": workflow_id, "lim": limit},
            )
        ).mappings()
        return [r["name"] for r in rows]
