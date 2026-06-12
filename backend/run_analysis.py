import asyncio
import os
import uuid
import logging

from app.database import async_session_factory
from app.models import Repo
from app.services.analysis import run_repo_analysis
from sqlalchemy import select, text

logging.basicConfig(level=logging.INFO)

async def run():
    repo_id_str = "5118615f-bcf5-48c8-aebc-47d59b5999b2"
    repo_id = uuid.UUID(repo_id_str)
    
    async with async_session_factory() as session:
        # Get the repo
        repo = (await session.execute(select(Repo).where(Repo.id == repo_id))).scalar_one_or_none()
        if not repo:
            print("Repo not found")
            return
            
        print(f"Starting analysis for {repo.name} ({repo.id})")
        # Run analysis (which drops and recreates edges/nodes for the repo)
        await run_repo_analysis(repo.id, repo.user_id)
        print("Analysis complete.")
        
        # Check edges count
        edges_count = (await session.execute(text(f"SELECT COUNT(*) FROM edges WHERE repo_id = '{repo.id}'"))).scalar()
        print(f"Total edges: {edges_count}")
        
        edges_by_type = (await session.execute(text(f"SELECT edge_type, COUNT(*) FROM edges WHERE repo_id = '{repo.id}' GROUP BY edge_type"))).fetchall()
        print("\nEdges by type:")
        for etype, count in edges_by_type:
            print(f"  {etype}: {count}")

if __name__ == "__main__":
    asyncio.run(run())
