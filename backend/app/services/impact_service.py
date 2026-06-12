"""Impact service facade — delegates to Change Intelligence Pipeline."""

from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.impact import ImpactResult
from app.services.impact_engines.pipeline import ChangeIntelligencePipeline


class ImpactService:
    def __init__(self) -> None:
        self._pipeline = ChangeIntelligencePipeline()

    async def analyze(
        self,
        query: str,
        repo_id: str,
        max_depth: int,
        direction: str,
        db: AsyncSession,
        *,
        natural_language: bool = True,
        repo_name: str = "",
        scenario: str = "modify",
    ) -> ImpactResult:
        return await self._pipeline.analyze(
            query=query,
            repo_id=repo_id,
            max_depth=max_depth,
            direction=direction,
            db=db,
            natural_language=natural_language,
            repo_name=repo_name,
            scenario=scenario,
        )
