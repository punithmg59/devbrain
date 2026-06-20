"""Full schema audit + fix: compare SQLAlchemy models vs PostgreSQL and add missing columns."""
import asyncio
import ssl

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

DATABASE_URL = "postgresql+asyncpg://postgres.cikvxankonaacgpnazyk:sp0905%40yp143@aws-1-ap-south-1.pooler.supabase.com:5432/postgres"

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

# Expected columns from SQLAlchemy models
EXPECTED = {
    "nodes": [
        "id", "repo_id", "file_id", "node_type", "name", "full_path",
        "start_line", "end_line", "raw_code", "signature",
        "calls", "called_by", "imports",
        "http_method", "route_path", "summary",
        "detailed_explanation", "architecture_role", "complexity_level",
        "call_flow_diagram", "ai_tags", "potential_risks",
        "tags", "is_exported", "is_async", "complexity_score",
        "created_at", "updated_at",
    ],
    "edges": [
        "id", "repo_id", "from_node_id", "to_node_id",
        "edge_type", "weight", "created_at",
    ],
    "repo_files": [
        "id", "repo_id", "file_path", "file_name", "extension", "language",
        "folder_path", "depth", "size_bytes", "line_count",
        "content_preview", "s3_key", "importance_score",
        "created_at", "updated_at",
    ],
    "repos": [
        "id", "user_id", "github_repo_id", "full_name", "name", "description",
        "default_branch", "is_private", "language", "analysis_status",
        "last_analyzed_at", "total_files", "total_functions", "total_lines",
        "created_at", "updated_at",
    ],
    "folder_tree": [
        "id", "repo_id", "folder_path", "folder_name", "parent_path",
        "depth", "file_count", "function_count", "created_at",
    ],
}

# Column DDL for missing columns (only for nodes since that is where mismatches are)
COLUMN_DDL = {
    "detailed_explanation": "TEXT",
    "architecture_role": "VARCHAR(255)",
    "complexity_level": "VARCHAR(20)",
    "call_flow_diagram": "TEXT",
    "ai_tags": "JSONB DEFAULT '[]'::jsonb",
    "potential_risks": "JSONB DEFAULT '[]'::jsonb",
}


async def audit_and_fix():
    engine = create_async_engine(DATABASE_URL, connect_args={"ssl": ctx, "statement_cache_size": 0})

    all_missing = {}

    # Phase 1: Audit
    async with engine.connect() as conn:
        for table, expected_cols in EXPECTED.items():
            print(f"\n{'='*60}")
            print(f"TABLE: {table}")
            print(f"{'='*60}")
            result = await conn.execute(text(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_schema = 'public' AND table_name = :t "
                "ORDER BY ordinal_position"
            ), {"t": table})
            db_cols = [row[0] for row in result.fetchall()]

            if not db_cols:
                print(f"  *** TABLE DOES NOT EXIST ***")
                continue

            missing = [c for c in expected_cols if c not in db_cols]
            extra = [c for c in db_cols if c not in expected_cols]

            print(f"  DB columns:    {len(db_cols)} -> {db_cols}")
            print(f"  Model columns: {len(expected_cols)}")

            if missing:
                print(f"  MISSING IN DB: {missing}")
                all_missing[table] = missing
            else:
                print(f"  OK - All model columns exist in DB")

            if extra:
                print(f"  Extra in DB (not in model): {extra}")

    # Phase 2: Fix missing columns
    if all_missing:
        print(f"\n{'='*60}")
        print("FIXING MISSING COLUMNS")
        print(f"{'='*60}")
        async with engine.begin() as conn:
            for table, missing_cols in all_missing.items():
                for col in missing_cols:
                    ddl = COLUMN_DDL.get(col)
                    if not ddl:
                        print(f"  SKIP {table}.{col} - no DDL defined")
                        continue
                    sql = f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS {col} {ddl}"
                    try:
                        await conn.execute(text(sql))
                        print(f"  ADDED {table}.{col}")
                    except Exception as e:
                        print(f"  FAILED {table}.{col}: {e}")

    # Phase 3: Re-verify
    print(f"\n{'='*60}")
    print("RE-VERIFICATION")
    print(f"{'='*60}")
    async with engine.connect() as conn:
        for table, expected_cols in EXPECTED.items():
            result = await conn.execute(text(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_schema = 'public' AND table_name = :t "
                "ORDER BY ordinal_position"
            ), {"t": table})
            db_cols = [row[0] for row in result.fetchall()]
            missing = [c for c in expected_cols if c not in db_cols]
            if missing:
                print(f"  STILL MISSING in {table}: {missing}")
            else:
                print(f"  {table}: OK")

    await engine.dispose()


asyncio.run(audit_and_fix())
