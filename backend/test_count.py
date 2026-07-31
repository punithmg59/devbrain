import asyncio
import ssl
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy import Column, Integer, String
import os

DATABASE_URL = "postgresql+asyncpg://postgres.cikvxankonaacgpnazyk:sp0905%40yp143@aws-1-ap-south-1.pooler.supabase.com:5432/postgres"

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

Base = declarative_base()

class Node(Base):
    __tablename__ = "nodes"
    id = Column(Integer, primary_key=True)
    name = Column(String)

async def test():
    engine = create_async_engine(DATABASE_URL, connect_args={"ssl": ctx, "statement_cache_size": 0})
    async_session = sessionmaker(engine, class_=AsyncSession)
    
    async with async_session() as session:
        try:
            base_query = select(Node)
            count_query = select(func.count()).select_from(base_query.subquery())
            res = await session.execute(count_query)
            print("COUNT SUCCESS:", res.scalar())
        except Exception as e:
            print("COUNT FAILED:", e)

if __name__ == "__main__":
    import sys
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    asyncio.run(test())

