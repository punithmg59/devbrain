import asyncio
import ssl
from sqlalchemy import create_async_engine, select, func
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.asyncio import AsyncSession
import os

DATABASE_URL = "postgresql+asyncpg://postgres.cikvxankonaacgpnazyk:sp0905%40yp143@aws-1-ap-south-1.pooler.supabase.com:5432/postgres"

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

async def test():
    engine = create_async_engine(DATABASE_URL, connect_args={"ssl": ctx, "statement_cache_size": 0})
    async_session = sessionmaker(engine, class_=AsyncSession)
    
    async with async_session() as session:
        try:
            # try finding similarity function
            res = await session.execute(select(func.similarity("abc", "abc")))
            print("SIMILARITY EXISTS:", res.scalar())
        except Exception as e:
            print("SIMILARITY FAILED:", e)

if __name__ == "__main__":
    asyncio.run(test())
