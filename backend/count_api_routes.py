import asyncio
from app.database import async_session_factory
from app.models.node import Node
from sqlalchemy import select, func

async def main():
    async with async_session_factory() as db:
        result = await db.execute(select(func.count()).where(Node.node_type == 'api_route'))
        print('API route count:', result.scalar())

if __name__ == '__main__':
    asyncio.run(main())
