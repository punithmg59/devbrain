"""Reset the last failed job back to 'queued' so the worker picks it up again."""
import asyncio
from app.database import async_session_factory
from sqlalchemy import text

async def reset():
    async with async_session_factory() as db:
        # Reset the most recent failed job to queued
        result = await db.execute(text("""
            UPDATE analysis_jobs
            SET    status = 'queued',
                   current_stage = 'queued',
                   error_message = NULL,
                   started_at = NULL,
                   finished_at = NULL,
                   worker_id = NULL,
                   heartbeat_at = NULL,
                   progress_percent = 0,
                   files_processed = 0,
                   nodes_count = 0,
                   edges_count = 0
            WHERE  id = (
                SELECT id FROM analysis_jobs
                ORDER BY created_at DESC
                LIMIT 1
            )
            RETURNING id, status
        """))
        await db.commit()
        row = result.first()
        if row:
            print(f"Reset job {row[0]} to status={row[1]}")
        else:
            print("No jobs found")

asyncio.run(reset())
