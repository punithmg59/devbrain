"""
tests/test_worker_pool.py
--------------------------
Comprehensive unit and integration tests for Phase 2.3 — Worker Pool.
"""

from __future__ import annotations

import asyncio
import time
from typing import List

import pytest

from core.scheduler import Scheduler
from core.worker_pool import (
    Worker,
    WorkerContext,
    WorkerMetrics,
    WorkerPool,
    WorkerState,
)
from models.job import AnalysisJob, JobPriority, JobStatus
from models.repository import RepositoryFile
from utils.exceptions import WorkerError


# ---------------------------------------------------------------------------
# Test Helpers
# ---------------------------------------------------------------------------

def make_file(path: str = "src/app.py", language: str = "python") -> RepositoryFile:
    return RepositoryFile(
        path=path,
        name=path.rsplit("/", 1)[-1],
        extension=path.rsplit(".", 1)[-1],
        language=language,
    )


def make_job(
    file_path: str = "src/app.py",
    language: str = "python",
    max_retries: int = 2,
    priority: JobPriority = JobPriority.NORMAL,
) -> AnalysisJob:
    return AnalysisJob.from_repository_file(
        repository_id="repo-worker-test",
        file=make_file(file_path, language),
        priority=priority,
        max_retries=max_retries,
    )


# ---------------------------------------------------------------------------
# Worker Models Tests
# ---------------------------------------------------------------------------

def test_worker_state_enum_values():
    assert WorkerState.IDLE.value == "idle"
    assert WorkerState.BUSY.value == "busy"
    assert WorkerState.STOPPING.value == "stopping"
    assert WorkerState.STOPPED.value == "stopped"
    assert WorkerState.ERROR.value == "error"


def test_worker_metrics_defaults():
    metrics = WorkerMetrics(worker_id="w-1")
    assert metrics.worker_id == "w-1"
    assert metrics.jobs_completed == 0
    assert metrics.jobs_failed == 0
    assert metrics.jobs_retried == 0
    assert metrics.jobs_cancelled == 0
    assert metrics.total_execution_time_seconds == 0.0
    assert metrics.last_heartbeat is not None


def test_worker_context_defaults():
    ctx = WorkerContext(worker_id="w-1", job_timeout_seconds=15.0)
    assert ctx.worker_id == "w-1"
    assert ctx.job_timeout_seconds == 15.0


# ---------------------------------------------------------------------------
# Worker Initialization & Heartbeat Tests
# ---------------------------------------------------------------------------

def test_worker_initialization():
    w = Worker(worker_id="worker-alpha", job_timeout_seconds=10.0)
    assert w.worker_id == "worker-alpha"
    assert w.state == WorkerState.IDLE
    assert w.current_job_id is None


def test_worker_heartbeat_update():
    w = Worker(worker_id="w-1")
    t1 = w.metrics.last_heartbeat
    time.sleep(0.01)
    w.heartbeat()
    t2 = w.metrics.last_heartbeat
    assert t2 >= t1


# ---------------------------------------------------------------------------
# WorkerPool Lifecycle Tests (Async)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_worker_pool_start_and_stop():
    pool = WorkerPool(worker_count=4)
    scheduler = Scheduler()

    assert pool.worker_count == 4
    assert not pool.is_running

    await pool.start(scheduler)
    assert pool.is_running
    assert len(pool.workers) == 4

    await pool.stop(graceful=True)
    assert not pool.is_running
    assert pool.worker_count == 0


@pytest.mark.asyncio
async def test_worker_pool_invalid_worker_count():
    with pytest.raises(WorkerError):
        WorkerPool(worker_count=0)

    with pytest.raises(WorkerError):
        WorkerPool(worker_count=200)


# ---------------------------------------------------------------------------
# Job Execution & Placeholder Handling Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_worker_pool_executes_placeholder_jobs():
    scheduler = Scheduler()
    jobs = [make_job(file_path=f"src/file_{i}.py") for i in range(10)]
    scheduler.submit_many(jobs)

    pool = WorkerPool(worker_count=3)
    await pool.start(scheduler)

    # Wait for all jobs to complete
    for _ in range(50):
        if scheduler.is_idle() and scheduler.progress().completed == 10:
            break
        await asyncio.sleep(0.05)

    progress = scheduler.progress()
    assert progress.completed == 10
    assert progress.failed == 0

    metrics = pool.aggregate_metrics()
    assert metrics["jobs_completed"] == 10

    await pool.stop()


# ---------------------------------------------------------------------------
# Error Isolation Tests (Worker handles exceptions without crashing pool)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_error_isolation_failing_handler_does_not_crash_pool():
    scheduler = Scheduler()
    job1 = make_job(file_path="fail.py", max_retries=0)
    job2 = make_job(file_path="pass.py", max_retries=0)
    scheduler.submit_many([job1, job2])

    async def custom_handler(job: AnalysisJob) -> None:
        if job.file.path == "fail.py":
            raise RuntimeError("Simulated parser failure!")
        await asyncio.sleep(0.01)

    pool = WorkerPool(worker_count=2, job_handler=custom_handler)
    await pool.start(scheduler)

    # Wait for jobs to process
    for _ in range(50):
        if scheduler.is_idle():
            break
        await asyncio.sleep(0.05)

    progress = scheduler.progress()
    assert progress.completed == 1
    assert progress.failed == 1

    # Ensure worker pool is still healthy and running after the error
    health = pool.health_check()
    assert health["healthy"] is True

    await pool.stop()


# ---------------------------------------------------------------------------
# Timeout Protection Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_worker_job_timeout_handling():
    scheduler = Scheduler()
    slow_job = make_job(file_path="slow.py", max_retries=0)
    scheduler.submit(slow_job)

    async def slow_handler(job: AnalysisJob) -> None:
        await asyncio.sleep(1.0)  # Exceeds 0.1s timeout

    pool = WorkerPool(
        worker_count=1,
        job_timeout_seconds=0.1,
        job_handler=slow_handler,
    )
    await pool.start(scheduler)

    for _ in range(50):
        if scheduler.is_idle():
            break
        await asyncio.sleep(0.05)

    progress = scheduler.progress()
    assert progress.failed == 1

    stored_job = scheduler.get_job(slow_job.job_id)
    assert stored_job is not None
    assert "timed out" in stored_job.error

    await pool.stop()


# ---------------------------------------------------------------------------
# Retry Logic Integration Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_worker_retries_failed_job():
    scheduler = Scheduler()
    flaky_job = make_job(file_path="flaky.py", max_retries=2)
    scheduler.submit(flaky_job)

    attempts = 0

    async def flaky_handler(job: AnalysisJob) -> None:
        nonlocal attempts
        attempts += 1
        if attempts < 2:
            raise ValueError("Transient error on attempt 1")
        await asyncio.sleep(0.01)

    pool = WorkerPool(worker_count=1, job_handler=flaky_handler)
    await pool.start(scheduler)

    for _ in range(50):
        if scheduler.is_idle() and scheduler.progress().completed == 1:
            break
        await asyncio.sleep(0.05)

    progress = scheduler.progress()
    assert progress.completed == 1
    assert attempts == 2

    stored_job = scheduler.get_job(flaky_job.job_id)
    assert stored_job.retry_count == 1

    await pool.stop()


# ---------------------------------------------------------------------------
# Dynamic Scaling Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_dynamic_scaling_up_and_down():
    pool = WorkerPool(worker_count=2)
    scheduler = Scheduler()
    await pool.start(scheduler)

    assert pool.worker_count == 2

    # Scale up to 6
    await pool.scale(6)
    assert pool.worker_count == 6

    # Scale down to 3
    await pool.scale(3)
    assert pool.worker_count == 3

    await pool.stop()


@pytest.mark.asyncio
async def test_add_and_remove_worker():
    pool = WorkerPool(worker_count=2)
    scheduler = Scheduler()
    await pool.start(scheduler)

    # Add worker
    new_worker = await pool.add_worker()
    assert pool.worker_count == 3
    assert pool.get_worker(new_worker.worker_id) is not None

    # Remove specific worker
    removed = await pool.remove_worker(new_worker.worker_id)
    assert removed is not None
    assert removed.worker_id == new_worker.worker_id
    assert pool.worker_count == 2

    await pool.stop()


# ---------------------------------------------------------------------------
# Health Check & Aggregate Metrics Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_health_check_and_aggregate_metrics():
    pool = WorkerPool(worker_count=3)
    scheduler = Scheduler()
    await pool.start(scheduler)

    health = pool.health_check()
    assert health["healthy"] is True
    assert health["total_workers"] == 3
    assert health["stale_worker_count"] == 0

    metrics = pool.aggregate_metrics()
    assert metrics["worker_count"] == 3
    assert "worker_details" in metrics
    assert len(metrics["worker_details"]) == 3

    await pool.stop()
