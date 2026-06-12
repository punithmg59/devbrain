"""Engine 2b: Blast Radius Intelligence — multi-dimensional impact (no LLM)."""

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.blast_radius_service import BlastRadiusEngine


class BlastRadiusImpactEngine:
    def __init__(self) -> None:
        self._engine = BlastRadiusEngine()

    async def run(self, ctx, db: AsyncSession) -> None:
        await self._engine.calculate(ctx, db)
