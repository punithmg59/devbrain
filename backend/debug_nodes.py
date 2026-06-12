"""Debug script: query the nodes table directly to find out what's there."""
import asyncio
import sys
sys.path.insert(0, ".")

async def main():
    from app.database import engine
    from sqlalchemy import text

    async with engine.connect() as conn:
        # 1. Count all repos
        result = await conn.execute(text("SELECT id, full_name, analysis_status, total_files, total_functions FROM repos"))
        repos = result.fetchall()
        print(f"\n=== REPOS ({len(repos)}) ===")
        for r in repos:
            print(f"  id={r[0]}, name={r[1]}, status={r[2]}, files={r[3]}, functions={r[4]}")

        if not repos:
            print("No repos found!")
            return

        # Use the first completed repo
        repo_id = None
        for r in repos:
            if r[2] == "completed":
                repo_id = r[0]
                print(f"\nUsing repo: {r[1]} (id={repo_id})")
                break
        
        if not repo_id:
            repo_id = repos[0][0]
            print(f"\nNo completed repo, using first: {repos[0][1]} (id={repo_id})")

        # 2. Count nodes for this repo
        result = await conn.execute(text(
            "SELECT COUNT(*) FROM nodes WHERE repo_id = :rid"
        ), {"rid": repo_id})
        total = result.scalar()
        print(f"\n=== TOTAL NODES: {total} ===")

        # 3. Node type distribution
        result = await conn.execute(text(
            "SELECT node_type, COUNT(*) FROM nodes WHERE repo_id = :rid GROUP BY node_type ORDER BY COUNT(*) DESC"
        ), {"rid": repo_id})
        rows = result.fetchall()
        print("\n=== NODE TYPE DISTRIBUTION ===")
        for row in rows:
            print(f"  {row[0]}: {row[1]}")

        # 4. Sample nodes
        result = await conn.execute(text(
            "SELECT id, node_type, name, full_path FROM nodes WHERE repo_id = :rid LIMIT 10"
        ), {"rid": repo_id})
        samples = result.fetchall()
        print(f"\n=== SAMPLE NODES (first 10) ===")
        for s in samples:
            print(f"  id={s[0]}, type={s[1]}, name={s[2]}, path={s[3]}")

        # 5. Check if pg_trgm extension exists
        try:
            result = await conn.execute(text(
                "SELECT extname FROM pg_extension WHERE extname = 'pg_trgm'"
            ))
            ext = result.fetchone()
            if ext:
                print(f"\n=== pg_trgm extension: INSTALLED ===")
            else:
                print(f"\n=== pg_trgm extension: NOT INSTALLED ===")
        except Exception as e:
            print(f"\n=== pg_trgm check failed: {e} ===")

        # 6. Test the exact query the API uses (no search, no filter)
        try:
            result = await conn.execute(text(
                "SELECT COUNT(*) FROM nodes WHERE repo_id = :rid"
            ), {"rid": repo_id})
            count = result.scalar()
            print(f"\n=== API query (no filter): {count} nodes ===")
        except Exception as e:
            print(f"\n=== API query failed: {e} ===")

        # 7. Test the similarity function
        try:
            result = await conn.execute(text(
                "SELECT similarity('test', 'test')"
            ))
            sim = result.scalar()
            print(f"\n=== similarity() function works: {sim} ===")
        except Exception as e:
            print(f"\n=== similarity() function FAILED: {e} ===")
            print("  This means pg_trgm is not enabled, which would cause search to fail")

asyncio.run(main())
