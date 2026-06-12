import asyncio
import json
from sqlalchemy import text
from app.database import async_session_factory
from app.routers.repo_detail import get_node_dependencies
from app.models import User
import uuid

class MockUser:
    id = uuid.UUID('d0a4b753-48e0-4dc2-8dc1-2131eb7d0b3d') # we don't know the exact UUID, let's query it

async def main():
    async with async_session_factory() as db:
        r = await db.execute(text("SELECT id, user_id FROM repos LIMIT 1"))
        repo_id, user_id = r.first()
        
        n = await db.execute(text("SELECT id, name FROM nodes WHERE name='_batch_summarize' LIMIT 1"))
        node_id, name = n.first()

        class MUser:
            id = user_id
        
        try:
            res = await get_node_dependencies(str(repo_id), str(node_id), MUser(), db)
            print("Risk Score:", res.risk.score)
            print("Level:", res.risk.level)
            print("Reason:", res.risk.reason)
            print("Called By:", len(res.called_by))
            print("Calls:", len(res.calls))
            print("Database Usage:", len(res.reads_tables) + len(res.writes_tables) + len(res.updates_tables) + len(res.deletes_tables))
            print("Services:", len(res.services))
        except Exception as e:
            print("Error:", e)

if __name__ == '__main__':
    asyncio.run(main())
