import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.database import async_session_factory
from app.services.project_brain import get_project_brain_dashboard
from sqlalchemy import text

async def test():
    async with async_session_factory() as db:
        # get first repo
        res = await db.execute(text("SELECT id FROM repos LIMIT 1"))
        repo_id = res.scalar()
        if not repo_id:
            print("No repos found in database")
            return
            
        print(f"Testing with repo_id: {repo_id}")
        
        try:
            dashboard = await get_project_brain_dashboard(db, str(repo_id))
            print("Successfully executed queries!")
            print(f"Score: {dashboard.intelligence_score.total_score}")
            print(f"Arch Map: {dashboard.architecture_map}")
            print(f"Critical Functions: {len(dashboard.critical_functions)}")
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(test())
