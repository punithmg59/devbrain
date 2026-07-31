import asyncio
import logging
import sys

from app.database import async_session_factory
from app.models import AnalysisJob, Repo, User
from app.services.pipeline.orchestrator import run_pipeline
from sqlalchemy import select

logging.basicConfig(level=logging.INFO, stream=sys.stdout)

async def main():
    async with async_session_factory() as session:
        repo = (await session.execute(select(Repo).limit(1))).scalar_one_or_none()
        if not repo:
            print("No repo found!")
            return
        
        user = (await session.execute(select(User).where(User.id == repo.user_id))).scalar_one_or_none()
        
        job = AnalysisJob(
            repo_id=repo.id,
            user_id=user.id,
            status="queued",
        )
        session.add(job)
        await session.commit()
        
        print(f"\n--- Enqueued AnalysisJob {job.id} for repo {repo.full_name} ---")

if __name__ == "__main__":
    asyncio.run(main())
