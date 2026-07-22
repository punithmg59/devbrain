"""
tests/test_job_engine.py
-------------------------
Comprehensive integration, concurrency, stress, cancellation, retry, shutdown,
race condition, large queue, and benchmark tests for Phase 2.5 — Job Execution Engine.
"""

from __future__ import annotations

import asyncio
import time
from typing import List

import pytest

from core.execution_context import ExecutionContext
from core.job_engine import EngineExecutionSummary, JobExecutionEngine
from core.scheduler import Scheduler
from models.job import AnalysisJob, JobPriority, JobStatus
from models.repository import Repository, RepositoryFile
from pipeline.context import PipelineContext
from pipeline.parser import ParserStage
from pipeline.pipeline import Pipeline


# ---------------------------------------------------------------------------
# Test Helpers
# ---------------------------------------------------------------------------

def make_repository() -> Repository:
    return Repository(id="repo-engine-test", url="/tmp", name="engine-test-repo")


def make_file(path: str = "src/main.py", language: str = "python") -> RepositoryFile:
    return RepositoryFile(
        path=path,
        name=path.rsplit("/", 1)[-1],
        extension=path.rsplit(".", 1)[-1],
        language=language,
    )


def make_job(path: str = "src/main.py", max_retries: int = 2) -> AnalysisJob:
    return AnalysisJob.from_repository_file(
        repository_id="repo-engine-test",
        file=make_file(path),
        max_retries=max_retries,
    )


# ---------------------------------------------------------------------------
# Basic Integration Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_job_execution_engine_basic_flow():
    scheduler = Scheduler()
    jobs = [make_job(f"src/file_{i}.py") for i in range(10)]
    scheduler.submit_many(jobs)

    ctx = PipelineContext(run_id="run-basic-engine", repository=make_repository())
    engine = JobExecutionEngine(
        scheduler=scheduler,
        pipeline_context=ctx,
        worker_count=4,
    )

    summary = await engine.run_until_complete()

    assert isinstance(summary, EngineExecutionSummary)
    assert summary.total_jobs == 10
    assert summary.completed_jobs == 10
    assert summary.failed_jobs == 0
    assert summary.success_rate_percent == 100.0
    assert summary.elapsed_time_seconds > 0.0
    assert ctx.progress.processed_files == 10


# ---------------------------------------------------------------------------
# Concurrency Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_engine_concurrency_across_workers():
    scheduler = Scheduler()
    jobs = [make_job(f"src/file_{i}.py") for i in range(20)]
    scheduler.submit_many(jobs)

    active_concurrent_workers = 0
    max_observed_concurrency = 0
    lock = asyncio.Lock()

    async def concurrent_handler(exec_ctx: ExecutionContext) -> None:
        nonlocal active_concurrent_workers, max_observed_concurrency
        async with lock:
            active_concurrent_workers += 1
            if active_concurrent_workers > max_observed_concurrency:
                max_observed_concurrency = active_concurrent_workers

        await asyncio.sleep(0.02)

        async with lock:
            active_concurrent_workers -= 1

    ctx = PipelineContext(run_id="run-concurrency", repository=make_repository())
    engine = JobExecutionEngine(
        scheduler=scheduler,
        pipeline_context=ctx,
        worker_count=8,
        job_handler=concurrent_handler,
    )

    summary = await engine.run_until_complete()
    assert summary.completed_jobs == 20
    assert max_observed_concurrency > 1


# ---------------------------------------------------------------------------
# Retry & Error Isolation Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_engine_job_retry_and_recovery():
    scheduler = Scheduler()
    job_flaky = make_job("flaky.py", max_retries=2)
    job_normal = make_job("normal.py", max_retries=0)
    scheduler.submit_many([job_flaky, job_normal])

    attempts = {}

    async def retry_handler(exec_ctx: ExecutionContext) -> None:
        path = exec_ctx.repository_file.path
        attempts[path] = attempts.get(path, 0) + 1
        if path == "flaky.py" and attempts[path] == 1:
            raise ValueError("Transient first attempt failure")
        await asyncio.sleep(0.005)

    ctx = PipelineContext(run_id="run-retry", repository=make_repository())
    engine = JobExecutionEngine(
        scheduler=scheduler,
        pipeline_context=ctx,
        worker_count=2,
        job_handler=retry_handler,
    )

    summary = await engine.run_until_complete()
    assert summary.completed_jobs == 2
    assert attempts["flaky.py"] == 2
    assert summary.retried_jobs >= 1


# ---------------------------------------------------------------------------
# Cancellation Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_engine_cancellation_mid_execution():
    scheduler = Scheduler()
    jobs = [make_job(f"src/file_{i}.py") for i in range(50)]
    scheduler.submit_many(jobs)

    async def slow_handler(exec_ctx: ExecutionContext) -> None:
        await asyncio.sleep(0.1)

    ctx = PipelineContext(run_id="run-cancel", repository=make_repository())
    engine = JobExecutionEngine(
        scheduler=scheduler,
        pipeline_context=ctx,
        worker_count=4,
        job_handler=slow_handler,
    )

    # Cancel after 0.05 seconds
    async def cancel_later():
        await asyncio.sleep(0.05)
        engine.cancel()

    asyncio.create_task(cancel_later())
    summary = await engine.run_until_complete()

    assert summary.completed_jobs < 50
    assert engine._cancellation_token.is_cancelled


# ---------------------------------------------------------------------------
# Shutdown & Race Condition Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_engine_graceful_shutdown():
    scheduler = Scheduler()
    jobs = [make_job(f"src/file_{i}.py") for i in range(5)]
    scheduler.submit_many(jobs)

    ctx = PipelineContext(run_id="run-shutdown", repository=make_repository())
    engine = JobExecutionEngine(
        scheduler=scheduler,
        pipeline_context=ctx,
        worker_count=2,
    )

    summary = await engine.run_until_complete()
    assert summary.completed_jobs == 5
    assert not engine.worker_pool.is_running


# ---------------------------------------------------------------------------
# End-to-End Pipeline Integration Test
# ---------------------------------------------------------------------------

def test_full_pipeline_with_parser_stage_execution(dummy_repository_model: Repository):
    """Test full pipeline run through Discovery -> Scheduler -> Parser (Engine)."""
    ctx = PipelineContext(run_id="e2e-pipeline-test", repository=dummy_repository_model)
    pipeline = Pipeline()

    res_ctx = pipeline.run(ctx)

    assert "discovered_files" in res_ctx.metadata
    assert "scheduler" in res_ctx.metadata
    assert "engine_summary" in res_ctx.metadata

    summary = res_ctx.metadata["engine_summary"]
    assert summary["completed_jobs"] == len(res_ctx.metadata["discovered_files"])
    assert res_ctx.progress.processed_files == summary["completed_jobs"]


# ---------------------------------------------------------------------------
# Benchmarks (100, 1000, 10000 jobs)
# ---------------------------------------------------------------------------

@pytest.mark.benchmark
@pytest.mark.parametrize("job_count", [100, 1000, 10000])
def test_job_execution_engine_benchmark(job_count: int):
    """Benchmark performance across 100, 1,000, and 10,000 jobs."""
    scheduler = Scheduler()
    jobs = [make_job(f"src/pkg_{i // 100}/file_{i}.py") for i in range(job_count)]
    scheduler.submit_many(jobs)

    ctx = PipelineContext(run_id=f"benchmark-{job_count}", repository=make_repository())
    engine = JobExecutionEngine(
        scheduler=scheduler,
        pipeline_context=ctx,
        worker_count=16,
    )

    summary = asyncio.run(engine.run_until_complete())

    assert summary.total_jobs == job_count
    assert summary.completed_jobs == job_count
    assert summary.success_rate_percent == 100.0
    assert summary.elapsed_time_seconds > 0.0

    print(
        f"\n[BENCHMARK] {job_count} jobs: "
        f"Time={summary.elapsed_time_seconds:.3f}s | "
        f"QueueTime={summary.average_queue_time_ms:.2f}ms | "
        f"Throughput={summary.throughput_jobs_per_sec:.1f} jobs/s | "
        f"WorkerUtil={summary.worker_utilization_percent:.1f}% | "
        f"RAM={summary.memory_rss_mb:.1f}MB | CPU={summary.cpu_percent:.1f}%"
    )
