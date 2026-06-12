import asyncio
from sqlalchemy import text
from app.database import async_session_factory

async def main():
    async with async_session_factory() as db:
        res = await db.execute(text('SELECT id, analysis_status FROM repos'))
        print(res.fetchall())

if __name__ == '__main__':
    asyncio.run(main())
