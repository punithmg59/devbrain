"""Self-improvement from workflow feedback — adjusts confidence deterministically."""

from __future__ import annotations

import logging
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.workflow import Workflow, WorkflowFeedback

logger = logging.getLogger(__name__)

ACCEPT_BOOST = 0.04
REJECT_PENALTY = 0.08
MIN_CONFIDENCE = 0.50
MAX_CONFIDENCE = 0.98


class WorkflowLearningService:
    async def record_feedback(
        self,
        repo_id: UUID,
        query: str,
        workflow_id: UUID,
        *,
        accepted: bool,
        rejected: bool,
        db: AsyncSession,
    ) -> tuple[float | None, str]:
        wf = await db.get(Workflow, workflow_id)
        if not wf or wf.repo_id != repo_id:
            return None, "Workflow not found"

        db.add(
            WorkflowFeedback(
                repo_id=repo_id,
                query=query,
                workflow_id=workflow_id,
                accepted=accepted,
                rejected=rejected,
            )
        )

        if accepted and not rejected:
            wf.confidence = min(MAX_CONFIDENCE, wf.confidence + ACCEPT_BOOST)
            msg = "Workflow marked accurate; confidence increased."
        elif rejected and not accepted:
            wf.confidence = max(MIN_CONFIDENCE, wf.confidence - REJECT_PENALTY)
            msg = "Workflow marked incorrect; confidence decreased."
        else:
            msg = "Feedback recorded."

        await db.flush()
        return wf.confidence, msg

    async def success_rate(self, workflow_id: UUID, db: AsyncSession) -> float:
        result = await db.execute(
            select(
                func.count().filter(WorkflowFeedback.accepted.is_(True)),
                func.count().filter(WorkflowFeedback.rejected.is_(True)),
                func.count(),
            ).where(WorkflowFeedback.workflow_id == workflow_id)
        )
        accepted, rejected, total = result.one()
        if total == 0:
            return 0.5
        return accepted / max(1, accepted + rejected)
