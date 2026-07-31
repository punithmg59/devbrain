import asyncio
from app.database import engine
from sqlalchemy import text

async def check():
    async with engine.connect() as conn:
        nodes = (await conn.execute(text("SELECT COUNT(*) FROM nodes"))).scalar()
        edges = (await conn.execute(text("SELECT COUNT(*) FROM edges"))).scalar()
        files = (await conn.execute(text("SELECT COUNT(*) FROM repo_files"))).scalar()
        repos = (await conn.execute(text("SELECT id, full_name, analysis_status FROM repos"))).fetchall()
        print(f"REPOS: {repos}")
        print(f"NODES: {nodes}")
        print(f"EDGES: {edges}")
        print(f"FILES: {files}")

if __name__ == "__main__":
    asyncio.run(check())
