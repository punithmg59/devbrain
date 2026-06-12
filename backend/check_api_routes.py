import asyncio
from sqlalchemy import text
from app.database import async_session_factory
from app.services.analysis import run_repo_analysis

async def main():
    async with async_session_factory() as db:
        result = await db.execute(text("SELECT id, user_id FROM repos LIMIT 1"))
        row = result.first()
        if not row:
            print('No repo found')
            return
        repo_id, user_id = row
        await run_repo_analysis(repo_id, user_id)
        result2 = await db.execute(text("SELECT COUNT(*) FROM nodes WHERE node_type='api_route'"))
        print('API route count after analysis:', result2.scalar())

if __name__ == '__main__':
    asyncio.run(main())
