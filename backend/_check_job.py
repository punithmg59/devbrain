import asyncio
from app.database import async_session_factory
from sqlalchemy import text

async def check():
    async with async_session_factory() as db:
        result = await db.execute(text(
            "SELECT id, status, current_stage, error_message, "
            "files_processed, nodes_count, edges_count "
            "FROM analysis_jobs ORDER BY created_at DESC LIMIT 1"
        ))
        row = result.first()
        print('Status:', row[1])
        print('Stage:', row[2])
        print('Error:', row[3])
        print('Files:', row[4])
        print('Nodes:', row[5])
        print('Edges:', row[6])
        if row[1] in ('completed', 'completed_with_warnings'):
            print('CHECK 4 PASSED - job completed successfully')
        else:
            print(f'CHECK 4 FAILED - job status: {row[1]} - {row[3]}')

asyncio.run(check())
