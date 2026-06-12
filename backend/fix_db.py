import asyncio
from sqlalchemy import text
from app.database import async_session_factory

async def main():
    async with async_session_factory() as db:
        await db.execute(text("UPDATE repos SET analysis_status = 'completed' WHERE id = '5118615f-bcf5-48c8-aebc-47d59b5999b2'"))
        await db.commit()
        print('Fixed status')

if __name__ == '__main__':
    asyncio.run(main())
