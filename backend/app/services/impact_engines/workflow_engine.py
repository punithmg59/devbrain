"""Engine 4: Workflow Intelligence — DB-backed workflows, services, journeys (no LLM)."""

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.workflow_impact_service import WorkflowImpactService


class WorkflowImpactEngine:
    def __init__(self) -> None:
        self._impact = WorkflowImpactService()

    async def run(self, ctx, db: AsyncSession) -> None:
        await self._impact.analyze(ctx, db)
