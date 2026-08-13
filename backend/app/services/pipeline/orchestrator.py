import asyncio
import logging
import os
import socket
import time
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select, text, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import async_session_factory, engine
from app.models.analysis_job import AnalysisJob, TERMINAL
from app.models.repo import Repo
from app.models.file import RepoFile
from app.models.user import User
from app.models.node import Node
from app.models.edge import Edge
from app.services.pipeline.progress import ProgressReporter
from app.services.pipeline.resilience import CloneError, PipelineError
from app.services.pipeline.file_scanner import scan, ScanResult
from app.services.pipeline.incremental import build_incremental_plan
from app.services.pipeline.graph_scorer import compute_scores
from app.services.pipeline.bulk_writer import (
    bulk_upsert_nodes, bulk_upsert_edges, update_file_hashes
)

logger = logging.getLogger(__name__)

# Unique identifier for this worker process instance.
# Used in heartbeat so we can detect stale jobs from dead workers.
WORKER_ID = f"{socket.gethostname()}:{os.getpid()}"

# Maximum simultaneous pipeline runs in this process.
# Increase via ANALYSIS_CONCURRENCY env var for larger servers.
_CONCURRENCY = int(os.getenv("ANALYSIS_CONCURRENCY", "3"))
_SEM = asyncio.Semaphore(_CONCURRENCY)

# Seconds of no heartbeat before a job is considered orphaned
# and eligible for reclaim by any worker.
HEARTBEAT_STALE_SECONDS = 90

# How often (seconds) the heartbeat keepalive task refreshes heartbeat_at.
_HEARTBEAT_INTERVAL = 30

# ── In-process job tracking ──────────────────────────────────────────────────
# Prevents the same process from reclaiming a job it is already running.
# This is the primary defense against the duplicate-execution bug: the claim
# query can see a stale heartbeat for a job that is still actively running
# in this process (because run_repo_analysis is synchronous and does not yield
# to the heartbeat task often enough). By tracking running jobs in-memory,
# _claim_next_job() will never return a job that is already in-flight.
_running_jobs: set[UUID] = set()


# ── Job claiming ─────────────────────────────────────────────────────────────

def _get_dialect_name() -> str:
    """Return the current SQLAlchemy dialect name ('sqlite' or 'postgresql')."""
    return engine.dialect.name


def _stale_heartbeat_expr(dialect: str) -> str:
    """Return SQL fragment for 'heartbeat is stale' appropriate for the dialect."""
    if dialect == "sqlite":
        return f"heartbeat_at < datetime('now', '-{HEARTBEAT_STALE_SECONDS} seconds')"
    # PostgreSQL
    return f"heartbeat_at < NOW() - INTERVAL '{HEARTBEAT_STALE_SECONDS} seconds'"


async def _claim_next_job() -> tuple[UUID | None, str | None]:
    """Atomically claim the next eligible job from the queue.

    A job is eligible if:
    - status = 'queued', OR
    - status is non-terminal AND heartbeat is stale (dead worker recovery)

    Jobs already running in this process (_running_jobs) are excluded.

    Implementation is dialect-aware:
    - PostgreSQL: SELECT ... FOR UPDATE SKIP LOCKED + UPDATE (original strategy)
    - SQLite:     SELECT + conditional UPDATE in one transaction (no FOR UPDATE)
    """
    dialect = _get_dialect_name()

    async with async_session_factory() as db:
        # Build exclusion list from in-process running jobs.
        # Use a nil UUID sentinel when the set is empty (avoids empty IN list).
        exclude_ids = list(_running_jobs) if _running_jobs else [
            UUID("00000000-0000-0000-0000-000000000000")
        ]
        exclude_strs = [str(uid) for uid in exclude_ids]

        from sqlalchemy import bindparam
        stale_expr = _stale_heartbeat_expr(dialect)

        if dialect == "postgresql":
            # ── PostgreSQL: use FOR UPDATE SKIP LOCKED for true row-level locking ──
            candidate = (await db.execute(
                text(f"""
                    SELECT id, status, heartbeat_at, created_at, worker_id
                    FROM analysis_jobs
                    WHERE id NOT IN :exclude_ids
                    AND (
                        status = 'queued'
                        OR (
                            status NOT IN ('completed', 'completed_with_warnings', 'failed')
                            AND (
                                heartbeat_at IS NULL
                                OR {stale_expr}
                            )
                        )
                    )
                    ORDER BY created_at ASC
                    LIMIT 1
                    FOR UPDATE SKIP LOCKED
                """).bindparams(bindparam("exclude_ids", expanding=True)),
                {"exclude_ids": exclude_strs},
            )).first()

            if not candidate:
                return None, None

            cand_id = candidate[0]
            cand_status = candidate[1]
            match_reason = (
                "status='queued'" if cand_status == "queued" else "stale_heartbeat"
            )

            logger.info(
                "Claiming job %s (reason: %s, prior_status: %s)",
                cand_id, match_reason, cand_status,
            )

            result = await db.execute(text("""
                UPDATE analysis_jobs
                SET    status       = 'cloning',
                       worker_id   = :worker_id,
                       heartbeat_at = NOW(),
                       started_at  = COALESCE(started_at, NOW())
                WHERE  id = :job_id
                RETURNING id
            """), {"worker_id": WORKER_ID, "job_id": cand_id})
            await db.commit()
            row = result.first()
            return (UUID(str(row[0])), match_reason) if row else (None, None)

        else:
            # ── SQLite: atomic conditional UPDATE (no FOR UPDATE SKIP LOCKED) ──
            # Strategy:
            #   1. SELECT candidate without lock.
            #   2. Immediately attempt conditional UPDATE WHERE status still matches.
            #   3. Only one concurrent transaction can succeed; the other gets 0 rows.
            # This is safe because SQLite uses file-level write locking — only one
            # writer can hold the write lock at a time, making step 2 atomic.

            candidate = (await db.execute(
                text(f"""
                    SELECT id, status, heartbeat_at, created_at, worker_id
                    FROM analysis_jobs
                    WHERE id NOT IN :exclude_ids
                    AND (
                        status = 'queued'
                        OR (
                            status NOT IN ('completed', 'completed_with_warnings', 'failed')
                            AND (
                                heartbeat_at IS NULL
                                OR {stale_expr}
                            )
                        )
                    )
                    ORDER BY created_at ASC
                    LIMIT 1
                """).bindparams(bindparam("exclude_ids", expanding=True)),
                {"exclude_ids": exclude_strs},
            )).first()

            if not candidate:
                return None, None

            cand_id = candidate[0]
            cand_status = candidate[1]
            match_reason = (
                "status='queued'" if cand_status == "queued" else "stale_heartbeat"
            )

            logger.info(
                "Claiming job %s (reason: %s, prior_status: %s)",
                cand_id, match_reason, cand_status,
            )

            # Atomic conditional UPDATE: only succeeds if the job is still in
            # the claimable state we found above. A concurrent worker that
            # already claimed it will have changed the status, so our WHERE
            # condition will not match and rowcount will be 0.
            now_str = "datetime('now')"
            if cand_status == "queued":
                where_clause = "status = 'queued'"
            else:
                # Stale reclaim: job must still be non-terminal AND still stale
                where_clause = f"""
                    status NOT IN ('completed', 'completed_with_warnings', 'failed', 'cloning', 'queued')
                    AND (heartbeat_at IS NULL OR {stale_expr})
                """

            result = await db.execute(text(f"""
                UPDATE analysis_jobs
                SET    status       = 'cloning',
                       worker_id   = :worker_id,
                       heartbeat_at = {now_str},
                       started_at  = COALESCE(started_at, {now_str})
                WHERE  id = :job_id
                AND    ({where_clause})
            """), {"worker_id": WORKER_ID, "job_id": str(cand_id)})
            await db.commit()

            if result.rowcount == 0:
                # Another worker claimed this job between our SELECT and UPDATE.
                logger.debug("Job %s already claimed by another worker — skipping", cand_id)
                return None, None

            return (UUID(str(cand_id)), match_reason)


# ── Heartbeat keepalive ──────────────────────────────────────────────────────

async def _heartbeat_keepalive(job_id: UUID, stop: asyncio.Event) -> None:
    """Background task that refreshes heartbeat_at every _HEARTBEAT_INTERVAL seconds.

    Runs alongside the analysis so the heartbeat never goes stale while
    the worker is alive and actively processing. Exits when stop is set.
    Uses dialect-appropriate SQL for the timestamp update.
    """
    dialect = _get_dialect_name()
    now_expr = "datetime('now')" if dialect == "sqlite" else "NOW()"

    while not stop.is_set():
        try:
            await asyncio.wait_for(stop.wait(), timeout=_HEARTBEAT_INTERVAL)
            # stop was set — exit
            return
        except asyncio.TimeoutError:
            # Interval elapsed — refresh heartbeat
            pass

        try:
            async with async_session_factory() as db:
                await db.execute(text(f"""
                    UPDATE analysis_jobs
                    SET heartbeat_at = {now_expr}
                    WHERE id = :job_id
                """), {"job_id": str(job_id)})
                await db.commit()
        except Exception as exc:
            # Heartbeat refresh failure is non-fatal; log and continue.
            logger.warning("Heartbeat refresh failed for job %s: %s", job_id, exc)


# ── Helper functions for PostgreSQL integration ───────────────────────────────

# No longer needed - nodes and edges are already in PostgreSQL


# ── Pipeline runner ───────────────────────────────────────────────────────────

async def run_pipeline(job_id: UUID) -> None:
    """
    Drive a single analysis job through all pipeline stages.

    Stage sequence:
      cloning → scanning → parsing → building_graph → saving → completed

    Contract:
        - NEVER raises. Any unhandled exception marks the job failed.
        - Calls existing analysis service functions for the actual work.
        - Updates AnalysisJob row at every stage transition.
        - Sets final repo.analysis_status to completed/completed_with_warnings/failed.
        - Aborts immediately if run_repo_analysis() returns False (duplicate/error).
    """
    started_at = time.monotonic()

    # Start heartbeat keepalive so the job is never reclaimed while alive.
    hb_stop = asyncio.Event()
    hb_task = asyncio.create_task(_heartbeat_keepalive(job_id, hb_stop))

    async with async_session_factory() as db:
        # Load job and related entities
        job = (await db.execute(
            select(AnalysisJob).where(AnalysisJob.id == job_id)
        )).scalar_one_or_none()

        if not job:
            logger.error("run_pipeline: job %s not found", job_id)
            hb_stop.set()
            await hb_task
            return

        if job.status in TERMINAL:
            logger.info("run_pipeline: job %s already terminal (%s)", job_id, job.status)
            hb_stop.set()
            await hb_task
            return

        repo = (await db.execute(
            select(Repo).where(Repo.id == job.repo_id)
        )).scalar_one_or_none()

        if not repo:
            logger.error("run_pipeline: repo %s not found for job %s", job.repo_id, job_id)
            hb_stop.set()
            await hb_task
            return

        # Load user
        user = (await db.execute(
            select(User).where(User.id == job.user_id)
        )).scalar_one_or_none()

        reporter = ProgressReporter(db, job, repo)
        job.worker_id = WORKER_ID
        job.started_at = datetime.now(timezone.utc)

        try:
            # ── STAGE: cloning ──────────────────────────────────────────
            # Already set by _claim_next_job. Log that we are starting.
            logger.info("Pipeline starting for repo %s", repo.full_name)

            # ── STAGE: scanning ────────────────────────────────────────
            await reporter.set_stage("scanning")

            logger.info("Executing Repository Analyzer V2 pipeline for repo %s", repo.full_name)
            job.incremental = False

            # ── STAGE: parsing ────────────────────────────────────────
            await reporter.set_stage("parsing")

            # ── CALL EXISTING ANALYSIS LOGIC ────────────────────────────
            from app.services.analysis import run_repo_analysis

            analysis_ok = await run_repo_analysis(repo.id, user.id)

            # ── ABORT ON DUPLICATE / FAILURE ────────────────────────────
            # If run_repo_analysis returned False, it means the analysis
            # was skipped (already running on another task) or failed.
            # We must NOT continue to building_graph / GraphScorer / save
            # because the DB may have 0 rows or stale data for this repo.
            if not analysis_ok:
                logger.warning(
                    "run_pipeline: analysis returned False for job %s repo %s — aborting pipeline",
                    job_id, repo.full_name,
                )
                await reporter.fail("Analysis skipped (duplicate or error)")
                return

            # After the call returns, query the counts from the database
            node_count = (await db.execute(
                select(func.count()).where(Node.repo_id == repo.id)
            )).scalar() or 0

            edge_count = (await db.execute(
                select(func.count()).where(Edge.repo_id == repo.id)
            )).scalar() or 0

            file_count = (await db.execute(
                select(func.count()).where(RepoFile.repo_id == repo.id)
            )).scalar() or 0

            # Get function count from repo if available
            function_count = repo.total_functions or 0

            # ── STAGE: building_graph ─────────────────────────────────
            await reporter.set_stage("building_graph")

            # Query nodes and edges from PostgreSQL after analysis
            nodes_result = await db.execute(
                select(Node).where(Node.repo_id == repo.id)
            )
            nodes = nodes_result.scalars().all()

            edges_result = await db.execute(
                select(Edge).where(Edge.repo_id == repo.id)
            )
            edges = edges_result.scalars().all()

            # Compute blast radius scores using PostgreSQL
            try:
                scores = await compute_scores(str(repo.id))
                logger.info("Graph scores: %s", scores)
            except Exception as exc:
                # Scoring failure should not fail the whole pipeline
                logger.warning("Graph scoring failed: %s", exc)

            await reporter.set_graph_counts(
                nodes=node_count,
                edges=edge_count,
                functions=function_count,
                files=file_count,
            )
            
            await reporter.set_stage("saving")

            # ── FINALIZE ───────────────────────────────────────────────
            files_failed = job.files_failed or 0
            final = "completed" if files_failed == 0 else "completed_with_warnings"
            elapsed = time.monotonic() - started_at
            await reporter.finish(final, elapsed)

            logger.info(
                "Pipeline complete: job=%s repo=%s status=%s elapsed=%.1fs",
                job_id, repo.full_name, final, elapsed,
            )

        except CloneError as exc:
            await reporter.fail(f"Clone failed after retries: {exc}")

        except asyncio.CancelledError:
            await reporter.fail("Worker was cancelled or restarted")
            raise  # allow graceful shutdown to propagate

        except Exception as exc:
            logger.exception(
                "Unhandled exception in pipeline for job %s repo %s",
                job_id, repo.full_name if repo else "unknown",
            )
            await reporter.fail(f"{type(exc).__name__}: {exc}")

        finally:
            # Stop the heartbeat keepalive task
            hb_stop.set()
            await hb_task


# ── Worker loop ───────────────────────────────────────────────────────────────

async def worker_loop(stop_event: asyncio.Event) -> None:
    """
    Long-running async task. Polls for queued jobs and runs them.

    Concurrency:
        _SEM limits how many jobs run simultaneously in this process.
        Multiple processes can run worker_loop() simultaneously — they
        coordinate safely via _claim_next_job()'s SKIP LOCKED.

    Shutdown:
        When stop_event is set (FastAPI shutdown), the loop exits after
        the current poll cycle. Running jobs finish naturally unless
        they are cancelled by the event loop shutdown.

    Heartbeat:
        _claim_next_job() sets heartbeat_at. A background keepalive task
        refreshes it every 30 seconds while the pipeline runs. If a worker
        dies mid-job, the next call to _claim_next_job() will reclaim that
        job after HEARTBEAT_STALE_SECONDS (90s).
    """
    logger.info("DevBrain worker loop started (worker_id=%s, concurrency=%d)",
                WORKER_ID, _CONCURRENCY)

    while not stop_event.is_set():
        try:
            job_id, match_reason = await _claim_next_job()

            if job_id is None:
                # No work available. Sleep briefly then poll again.
                await asyncio.sleep(1.0)
                continue

            # Guard: skip if this process is already running this job.
            # This is belt-and-suspenders — _claim_next_job also excludes
            # _running_jobs, but this catches any race window.
            if job_id in _running_jobs:
                logger.warning(
                    "Job %s already running in this process — skipping duplicate claim",
                    job_id,
                )
                continue

            logger.info("Worker claimed job %s (reason: %s)", job_id, match_reason)

            # Acquire semaphore before launching task so we cap concurrency.
            await _SEM.acquire()

            async def run_and_release(jid: UUID) -> None:
                _running_jobs.add(jid)
                try:
                    await run_pipeline(jid)
                finally:
                    _running_jobs.discard(jid)
                    _SEM.release()

            asyncio.create_task(run_and_release(job_id))

        except asyncio.CancelledError:
            logger.info("Worker loop cancelled — shutting down")
            break
        except Exception as exc:
            # Worker loop itself must never crash.
            # Log and continue polling.
            logger.exception("Worker loop error (continuing): %s", exc)
            await asyncio.sleep(2.0)

    logger.info("Worker loop stopped")
