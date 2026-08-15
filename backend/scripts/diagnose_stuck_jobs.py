#!/usr/bin/env python3
"""
scripts/diagnose_stuck_jobs.py
------------------------------
Diagnostic script for Task 6: inspect analysis_jobs state and row counts.

Usage:
    cd d:/devbrain/backend
    python scripts/diagnose_stuck_jobs.py [repo_id1 repo_id2 ...]

    # Example with specific stuck repo IDs from production logs:
    python scripts/diagnose_stuck_jobs.py \
        36ec3278-39f6-47da-b3db-02a1c774f808 \
        b7439a9d-3eea-4a61-a293-066a5847f5e1

DO NOT delete any data. Read-only queries only.
"""

import asyncio
import os
import sys
from pathlib import Path

# Ensure app is importable
backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

# Load .env if present
try:
    from dotenv import load_dotenv
    load_dotenv(backend_dir / ".env")
except ImportError:
    pass


async def run_diagnostics(stuck_repo_ids: list[str]) -> None:
    from sqlalchemy import text
    from app.database import async_session_factory

    async with async_session_factory() as db:
        print("=" * 72)
        print("ANALYSIS JOBS — last 10 by created_at")
        print("=" * 72)
        rows = (await db.execute(text("""
            SELECT
                id,
                repo_id,
                status,
                current_stage,
                worker_id,
                heartbeat_at,
                created_at,
                started_at,
                finished_at,
                error_message
            FROM analysis_jobs
            ORDER BY created_at DESC
            LIMIT 10
        """))).fetchall()

        if not rows:
            print("  (no rows found)")
        for r in rows:
            hb = r.heartbeat_at
            created = r.created_at
            # Compute staleness
            stale_str = ""
            if hb:
                try:
                    from datetime import datetime, timezone
                    now = datetime.now(timezone.utc)
                    hb_dt = hb if hb.tzinfo else hb.replace(tzinfo=__import__('datetime').timezone.utc)
                    age = (now - hb_dt).total_seconds()
                    stale_str = f" [STALE {age:.0f}s]" if age > 90 else f" [alive {age:.0f}s ago]"
                except Exception:
                    stale_str = " [unknown]"
            print(
                f"  job_id={r.id}\n"
                f"    repo_id={r.repo_id}\n"
                f"    status={r.status}  stage={r.current_stage}\n"
                f"    worker_id={r.worker_id}\n"
                f"    created_at={created}  started_at={r.started_at}  finished_at={r.finished_at}\n"
                f"    heartbeat_at={hb}{stale_str}\n"
                f"    error={r.error_message!r}\n"
            )

        print()
        print("=" * 72)
        print("GLOBAL ROW COUNTS")
        print("=" * 72)
        for table in ("repo_files", "nodes", "edges"):
            count = (await db.execute(text(f"SELECT COUNT(*) FROM {table}"))).scalar()
            print(f"  {table}: {count:,} rows")

        if stuck_repo_ids:
            print()
            print("=" * 72)
            print("PER-REPO COUNTS for stuck repo_ids")
            print("=" * 72)
            for rid in stuck_repo_ids:
                print(f"\n  repo_id = {rid}")
                for table in ("repo_files", "nodes", "edges"):
                    try:
                        count = (await db.execute(
                            text(f"SELECT COUNT(*) FROM {table} WHERE repo_id = CAST(:rid AS uuid)"),
                            {"rid": rid},
                        )).scalar()
                        print(f"    {table}: {count:,} rows")
                    except Exception as exc:
                        print(f"    {table}: ERROR — {exc}")

                # Also show the most recent job for this repo
                job_row = (await db.execute(text("""
                    SELECT id, status, heartbeat_at, worker_id, created_at
                    FROM analysis_jobs
                    WHERE repo_id = CAST(:rid AS uuid)
                    ORDER BY created_at DESC
                    LIMIT 1
                """), {"rid": rid})).first()
                if job_row:
                    print(
                        f"    latest_job: id={job_row.id} status={job_row.status} "
                        f"worker={job_row.worker_id} hb={job_row.heartbeat_at} created={job_row.created_at}"
                    )
                else:
                    print("    latest_job: (none found)")

        print()
        print("=" * 72)
        print("ANALYSIS_JOBS STATUS SUMMARY")
        print("=" * 72)
        summary = (await db.execute(text("""
            SELECT status, COUNT(*) as cnt
            FROM analysis_jobs
            GROUP BY status
            ORDER BY cnt DESC
        """))).fetchall()
        for s in summary:
            print(f"  {s.status}: {s.cnt}")

        print()
        print("Done. No data was modified.")


def main() -> None:
    stuck_repo_ids = sys.argv[1:]  # optional positional args

    # Always include the known stuck repos from production logs
    known_stuck = [
        "36ec3278-39f6-47da-b3db-02a1c774f808",
        "b7439a9d-3eea-4a61-a293-066a5847f5e1",
    ]
    all_repo_ids = list(dict.fromkeys(known_stuck + stuck_repo_ids))

    asyncio.run(run_diagnostics(all_repo_ids))


if __name__ == "__main__":
    main()
