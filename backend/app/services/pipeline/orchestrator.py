import asyncio
import logging
import os
import socket
import time
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select, text, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import async_session_factory
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


# ── Job claiming ─────────────────────────────────────────────────────────────

async def _claim_next_job() -> UUID | None:
    """
    Atomically claim one queued job (or reclaim a stale in-progress job)
    using SELECT ... FOR UPDATE SKIP LOCKED.

    Returns the job UUID if one was claimed, None if the queue is empty.

    SKIP LOCKED means multiple worker processes can call this simultaneously
    without deadlocking — each gets a different job.
    """
    async with async_session_factory() as db:
        result = await db.execute(text("""
            UPDATE analysis_jobs
            SET    status       = 'cloning',
                   worker_id   = :worker_id,
                   heartbeat_at = now(),
                   started_at  = COALESCE(started_at, now())
            WHERE  id = (
                SELECT id FROM analysis_jobs
                WHERE  status = 'queued'
                OR (
                    status NOT IN ('completed', 'completed_with_warnings', 'failed')
                    AND (
                        heartbeat_at IS NULL
                        OR heartbeat_at < now() - interval '90 seconds'
                    )
                )
                ORDER BY created_at ASC
                LIMIT 1
                FOR UPDATE SKIP LOCKED
            )
            RETURNING id
        """), {"worker_id": WORKER_ID})
        await db.commit()
        row = result.first()
        return row[0] if row else None


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
    """
    started_at = time.monotonic()

    async with async_session_factory() as db:
        # Load job and related entities
        job = (await db.execute(
            select(AnalysisJob).where(AnalysisJob.id == job_id)
        )).scalar_one_or_none()

        if not job:
            logger.error("run_pipeline: job %s not found", job_id)
            return

        if job.status in TERMINAL:
            logger.info("run_pipeline: job %s already terminal (%s)", job_id, job.status)
            return

        repo = (await db.execute(
            select(Repo).where(Repo.id == job.repo_id)
        )).scalar_one_or_none()

        if not repo:
            logger.error("run_pipeline: repo %s not found for job %s", job.repo_id, job_id)
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

            # TODO: The existing analysis function handles cloning internally.
            # On Day 5, we will separate cloning from analysis to get the clone_path.
            # For now, we skip scanning since we don't have access to the clone path.
            # The scanner will be fully integrated when we refactor the analysis flow.
            clone_path = None  # Will be populated on Day 5

            if clone_path:
                # Run scanner in a thread (it uses os.walk which is I/O bound)
                scan_result = await asyncio.to_thread(scan, clone_path)

                await reporter.set_files_total(scan_result.analyzable_total)

                logger.info(
                    "Scan complete: %d total files, %d analyzable, fast_mode=%s",
                    scan_result.files_total, scan_result.analyzable_total, scan_result.fast_mode,
                )

                if scan_result.fast_mode and scan_result.skipped_dirs:
                    logger.info("Fast mode skipped top-level dirs: %s", scan_result.skipped_dirs)

                # ── INCREMENTAL PLAN ─────────────────────────────────────
                # Get current HEAD commit SHA if available
                head_sha = getattr(repo, "last_commit_sha", None)

                plan = await build_incremental_plan(db, str(repo.id), scan_result, head_sha)

                logger.info(
                    "Incremental plan: is_incremental=%s, to_parse=%d, unchanged=%d, deleted=%d",
                    plan.is_incremental, plan.changed_count,
                    plan.skipped_count, len(plan.deleted_paths),
                )

                job.incremental = plan.is_incremental

                # If nothing changed, finish immediately
                if plan.is_incremental and plan.changed_count == 0:
                    await reporter.finish("completed", time.monotonic() - started_at)
                    return
            else:
                # No clone path available - skip scanner for now
                logger.info("Skipping scanner (clone path not available - will integrate on Day 5)")
                job.incremental = False

            # ── STAGE: parsing ────────────────────────────────────────
            await reporter.set_stage("parsing")

            # ── CALL EXISTING ANALYSIS LOGIC ────────────────────────────
            # Import the existing analysis function
            from app.services.analysis import run_repo_analysis

            # Call the existing analysis function
            # This function handles the full analysis including:
            # - Cloning the repo
            # - Scanning files
            # - Parsing code
            # - Building graph (nodes + edges)
            # - Persisting to database
            await run_repo_analysis(repo.id, user.id)
            
            # After the call returns, query the counts from the database
            node_count = (await db.execute(
                select(func.count()).where(Node.repo_id == repo.id)
            )).scalar() or 0

            edge_count = (await db.execute(
                select(func.count()).where(Edge.repo_id == repo.id)
            )).scalar() or 0

            file_count = (await db.execute(
                select(func.count()).where(RepoFile.repo_id == repo.id)
            )).scalar() if hasattr(repo, 'files') else (job.files_total or 0)

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
        _claim_next_job() sets heartbeat_at. If a worker dies mid-job,
        the next call to _claim_next_job() will reclaim that job after
        HEARTBEAT_STALE_SECONDS (90s).
    """
    logger.info("DevBrain worker loop started (worker_id=%s, concurrency=%d)",
                WORKER_ID, _CONCURRENCY)

    while not stop_event.is_set():
        try:
            job_id = await _claim_next_job()

            if job_id is None:
                # No work available. Sleep briefly then poll again.
                await asyncio.sleep(1.0)
                continue

            logger.info("Worker claimed job %s", job_id)

            # Acquire semaphore before launching task so we cap concurrency.
            await _SEM.acquire()

            async def run_and_release(jid: UUID) -> None:
                try:
                    await run_pipeline(jid)
                finally:
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
