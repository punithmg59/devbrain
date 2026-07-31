import asyncio
import logging
import sys

from app.database import async_session_factory
from app.models import Repo
from app.services.pipeline.graph_scorer import compute_scores
from sqlalchemy import select

logging.basicConfig(level=logging.INFO, stream=sys.stdout)

async def main():
    async with async_session_factory() as session:
        repo = (await session.execute(select(Repo).limit(1))).scalar_one_or_none()
        if not repo:
            print("No repo found!")
            return
        
        print(f"\n--- Testing GraphScorer Instrumentation for Repo: {repo.full_name} ({repo.id}) ---")
        scores = await compute_scores(str(repo.id))
        print(f"\n--- Result Scores: {scores} ---")

if __name__ == "__main__":
    asyncio.run(main())
