import asyncio
from app.database import async_session_factory
from sqlalchemy import text

async def check():
    async with async_session_factory() as db:
        result = await db.execute(text("""
            SELECT table_name FROM information_schema.tables
            WHERE table_schema = 'public'
            AND table_name IN ('analysis_jobs', 'file_errors')
            ORDER BY table_name
        """))
        tables = [r[0] for r in result.all()]
        print('Tables found:', tables)
        
        # Check repos table for content_hash column
        result = await db.execute(text("""
            SELECT column_name FROM information_schema.columns
            WHERE table_schema = 'public' AND table_name = 'repos'
            AND column_name = 'content_hash'
        """))
        repos_content_hash = [r[0] for r in result.all()]
        print('repos.content_hash exists:', bool(repos_content_hash))
        
        # Check repo_files table for new columns
        result = await db.execute(text("""
            SELECT column_name FROM information_schema.columns
            WHERE table_schema = 'public' AND table_name = 'repo_files'
            AND column_name IN ('content_hash', 'last_commit_sha', 'last_analyzed_at')
            ORDER BY column_name
        """))
        repo_files_cols = [r[0] for r in result.all()]
        print('repo_files new columns:', repo_files_cols)

asyncio.run(check())
