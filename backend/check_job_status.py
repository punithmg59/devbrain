import asyncio
from app.database import engine
from sqlalchemy import text

async def check():
    async with engine.connect() as conn:
        job = (await conn.execute(text("SELECT id, status, current_stage, heartbeat_at, started_at, finished_at, worker_id, error_message FROM analysis_jobs WHERE id = '7eaa9e23-0f47-4ebe-ae79-c7ae93a901ed'"))).first()
        print(f"JOB STATUS: {job}")

if __name__ == "__main__":
    asyncio.run(check())
