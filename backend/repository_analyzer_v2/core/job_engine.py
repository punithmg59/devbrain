"""
core/job_engine.py
------------------
Phase 2.5 — Job Execution Engine & Scheduler + Worker Pool Integration.

Orchestrates the integration between Scheduler (Phase 2.2) and WorkerPool (Phase 2.3).
Executes all queued AnalysisJob units through asynchronous workers using
ExecutionContext (Phase 2.4).

Key Features
------------
- **End-to-End Orchestration**: Connects Repository Discovery → AnalysisJob Creation →
  Scheduler Queue → Worker Pool → ExecutionContext → Completion.
- **Progress & Metrics Integration**: Automatically updates PipelineContext progress
  and records CPU, RSS memory, worker utilization, and job duration metrics in MetricsCollector.
- **Structured Logging**: Emits contextual structured logs throughout the job processing lifecycle.
- **Fault Tolerance & Resilience**: Handles job retries, error isolation, cancellation signals,
  and graceful pool shutdown cleanly.
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Awaitable, Callable, Dict, List, Optional

from config.settings import AnalyzerSettings, get_settings
from core.execution_context import CancellationToken, ExecutionContext
from core.scheduler import Scheduler
from core.worker_pool import Worker, WorkerPool
from models.job import AnalysisJob
from pipeline.context import PipelineContext
from utils.logger import get_logger, set_log_context
from utils.metrics import MetricsCollector

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Execution Summary Data Class
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class EngineExecutionSummary:
    """Summary metrics of an integrated JobExecutionEngine run."""
    total_jobs: int
    completed_jobs: int
    failed_jobs: int
    retried_jobs: int
    skipped_jobs: int
    cancelled_jobs: int
    elapsed_time_seconds: float
    throughput_jobs_per_sec: float
    success_rate_percent: float
    average_queue_time_ms: float
    average_job_duration_ms: float
    worker_utilization_percent: float
    memory_rss_mb: float
    cpu_percent: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_jobs": self.total_jobs,
            "completed_jobs": self.completed_jobs,
            "failed_jobs": self.failed_jobs,
            "retried_jobs": self.retried_jobs,
            "skipped_jobs": self.skipped_jobs,
            "cancelled_jobs": self.cancelled_jobs,
            "elapsed_time_seconds": round(self.elapsed_time_seconds, 4),
            "throughput_jobs_per_sec": round(self.throughput_jobs_per_sec, 2),
            "success_rate_percent": round(self.success_rate_percent, 2),
            "average_queue_time_ms": round(self.average_queue_time_ms, 2),
            "average_job_duration_ms": round(self.average_job_duration_ms, 2),
            "worker_utilization_percent": round(self.worker_utilization_percent, 2),
            "memory_rss_mb": round(self.memory_rss_mb, 2),
            "cpu_percent": round(self.cpu_percent, 2),
        }


# ---------------------------------------------------------------------------
# Job Execution Engine Class
# ---------------------------------------------------------------------------

class JobExecutionEngine:
    """
    High-level orchestrator connecting Scheduler and WorkerPool.
    """

    def __init__(
        self,
        scheduler: Scheduler,
        pipeline_context: PipelineContext,
        worker_count: int = 4,
        job_timeout_seconds: float = 30.0,
        job_handler: Optional[Callable[[ExecutionContext], Awaitable[None]]] = None,
        config: Optional[AnalyzerSettings] = None,
        metrics_collector: Optional[MetricsCollector] = None,
    ) -> None:
        self.scheduler: Scheduler = scheduler
        self.pipeline_context: PipelineContext = pipeline_context
        self.config: AnalyzerSettings = config or get_settings()
        self.metrics_collector: MetricsCollector = metrics_collector or MetricsCollector.get_instance()
        self._custom_handler = job_handler

        # Instantiates WorkerPool with context wrapper handler
        self.worker_pool: WorkerPool = WorkerPool(
            worker_count=worker_count,
            job_timeout_seconds=job_timeout_seconds,
            job_handler=self._wrap_execution_context,
        )

        self._cancellation_token: CancellationToken = CancellationToken()
        self._queue_times_ms: List[float] = []
        self._job_durations_ms: List[float] = []
        self._worker_utilization_samples: List[float] = []
        self._lock = asyncio.Lock()

    async def _wrap_execution_context(self, job: AnalysisJob) -> None:
        """
        Worker callback wrapper: wraps AnalysisJob into ExecutionContext,
        invokes job_handler, updates progress, and records metrics.
        """
        # Calculate queue time
        queue_time_ms = 0.0
        if job.created_at:
            now = datetime.now(timezone.utc)
            queue_time_ms = max(0.0, (now - job.created_at).total_seconds() * 1000.0)

        async with self._lock:
            self._queue_times_ms.append(queue_time_ms)

        # Retrieve current worker reference if available
        current_task_name = asyncio.current_task().get_name() if asyncio.current_task() else ""
        worker_id = current_task_name.replace("WorkerTask-", "") if "WorkerTask-" in current_task_name else "worker-unknown"
        worker = self.worker_pool.get_worker(worker_id) or Worker(worker_id=worker_id)

        # Create ExecutionContext for this job run
        exec_ctx = ExecutionContext(
            job=job,
            worker=worker,
            pipeline_context=self.pipeline_context,
            metrics=self.metrics_collector,
            config=self.config,
            timeout_seconds=self.worker_pool.job_timeout_seconds,
            cancellation_token=self._cancellation_token,
        )

        start_t = time.monotonic()
        set_log_context(
            analysis_id=self.pipeline_context.run_id,
            repository_id=self.pipeline_context.repository_id,
        )

        try:
            if self._custom_handler:
                await self._custom_handler(exec_ctx)
            else:
                # Default placeholder execution
                await asyncio.sleep(0.005)

            # Update progress
            self.pipeline_context.progress.increment(1)
            duration_ms = (time.monotonic() - start_t) * 1000.0

            async with self._lock:
                self._job_durations_ms.append(duration_ms)

        except asyncio.CancelledError:
            exec_ctx.add_warning(f"Execution cancelled for file {job.file.path}")
            raise
        except Exception as exc:
            exec_ctx.add_error(f"Job execution error on {job.file.path}: {exc}")
            raise

    def cancel(self) -> None:
        """Signal engine cancellation."""
        self._cancellation_token.cancel()
        logger.info(f"[Engine] Cancellation requested for run_id={self.pipeline_context.run_id}")

    async def run_until_complete(self, poll_interval_seconds: float = 0.05) -> EngineExecutionSummary:
        """
        Execute all queued jobs through WorkerPool until scheduler queue is drained.

        :param poll_interval_seconds: Polling interval for checking completion status.
        :return: EngineExecutionSummary metrics summary.
        """
        logger.info(
            f"[Engine] Starting execution engine for repository '{self.pipeline_context.repository_id}' "
            f"({self.scheduler.pending_count()} job(s) queued, {self.worker_pool.worker_count} worker(s))"
        )

        start_time = time.monotonic()
        if self.pipeline_context.progress.total_files == 0:
            self.pipeline_context.progress.total_files = self.scheduler.progress().total

        # Start worker pool
        await self.worker_pool.start(self.scheduler)

        try:
            while not self.scheduler.is_idle() and not self._cancellation_token.is_cancelled:
                # Update worker utilization in metrics
                busy_workers = sum(1 for w in self.worker_pool.workers if w.state.value == "busy")
                utilization = (busy_workers / self.worker_pool.worker_count) * 100.0 if self.worker_pool.worker_count > 0 else 0.0
                
                self._worker_utilization_samples.append(utilization)
                self.metrics_collector.record_worker_utilization(
                    self.pipeline_context.run_id,
                    busy_workers,
                    self.worker_pool.worker_count,
                )

                await asyncio.sleep(poll_interval_seconds)

            if self._cancellation_token.is_cancelled:
                logger.warning(f"[Engine] Execution interrupted by cancellation token.")

        finally:
            # Stop worker pool gracefully
            await self.worker_pool.stop(graceful=True)

        elapsed = max(0.0001, time.monotonic() - start_time)
        sched_progress = self.scheduler.progress()
        sched_stats = self.scheduler.statistics()

        # Compute aggregate summary
        avg_queue_time = sum(self._queue_times_ms) / len(self._queue_times_ms) if self._queue_times_ms else 0.0
        avg_duration = sum(self._job_durations_ms) / len(self._job_durations_ms) if self._job_durations_ms else 0.0
        throughput = sched_progress.done / elapsed
        success_rate = sched_progress.success_rate

        res_snapshot = self.metrics_collector.get_system_resource_usage()
        avg_utilization = sum(self._worker_utilization_samples) / max(1, len(self._worker_utilization_samples))

        summary = EngineExecutionSummary(
            total_jobs=sched_progress.total,
            completed_jobs=sched_progress.completed,
            failed_jobs=sched_progress.failed,
            retried_jobs=sched_progress.retrying + sched_stats.total_retries,
            skipped_jobs=sched_progress.skipped,
            cancelled_jobs=sched_progress.cancelled,
            elapsed_time_seconds=elapsed,
            throughput_jobs_per_sec=throughput,
            success_rate_percent=success_rate,
            average_queue_time_ms=avg_queue_time,
            average_job_duration_ms=avg_duration,
            worker_utilization_percent=avg_utilization,
            memory_rss_mb=res_snapshot["memory_rss_mb"],
            cpu_percent=res_snapshot["cpu_percent"],
        )

        logger.info(
            f"[Engine] Completed run in {elapsed:.3f}s: {summary.completed_jobs}/{summary.total_jobs} "
            f"completed ({summary.success_rate_percent:.1f}% success, {summary.throughput_jobs_per_sec:.1f} jobs/sec)"
        )

        return summary
