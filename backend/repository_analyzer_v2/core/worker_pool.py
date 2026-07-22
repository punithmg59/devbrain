"""
core/worker_pool.py
-------------------
Phase 2.3 — Worker Pool & Async Execution System.

Provides an isolated, fault-tolerant, async worker pool for executing
AnalysisJob units dispatched by the Scheduler.

Key Features
------------
- **Worker Isolation**: Worker crashes or uncaught exceptions in job handlers
  are isolated. A failing worker logs the error, updates metrics, marks the job
  failed/retried, and returns to IDLE state to process subsequent jobs.
- **Async Execution**: Powered by `asyncio` for non-blocking I/O and high concurrency.
- **Dynamic Scaling**: Scale pool size up or down dynamically at runtime via
  `scale()`, `add_worker()`, or `remove_worker()`.
- **Heartbeat & Health Checks**: Every worker updates its timestamp on every loop iteration,
  allowing `WorkerPool.health_check()` to detect hung or stalled workers.
- **Timeouts & Cancellation**: Enforces per-job timeout limits via `asyncio.wait_for()`,
  gracefully handling job cancellation signals.
- **Metrics Collection**: Aggregates throughput, failures, retries, and total execution
  time per worker and across the pool.
"""

from __future__ import annotations

import asyncio
import logging
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Awaitable, Callable, Dict, List, Optional, Set

from core.scheduler import Scheduler
from models.job import AnalysisJob, JobStatus
from utils.exceptions import ErrorCode, WorkerError

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Worker State & Context Models
# ---------------------------------------------------------------------------

class WorkerState(str, Enum):
    """Lifecycle states of an individual worker in the pool."""
    IDLE = "idle"
    BUSY = "busy"
    STOPPING = "stopping"
    STOPPED = "stopped"
    ERROR = "error"


@dataclass
class WorkerMetrics:
    """Operational metrics tracked per worker instance."""
    worker_id: str
    jobs_completed: int = 0
    jobs_failed: int = 0
    jobs_retried: int = 0
    jobs_cancelled: int = 0
    total_execution_time_seconds: float = 0.0
    last_heartbeat: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "worker_id": self.worker_id,
            "jobs_completed": self.jobs_completed,
            "jobs_failed": self.jobs_failed,
            "jobs_retried": self.jobs_retried,
            "jobs_cancelled": self.jobs_cancelled,
            "total_execution_time_seconds": round(self.total_execution_time_seconds, 4),
            "last_heartbeat": self.last_heartbeat.isoformat(),
        }


@dataclass
class WorkerContext:
    """Execution context provided to an individual worker."""
    worker_id: str
    job_timeout_seconds: float = 30.0
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


# ---------------------------------------------------------------------------
# Individual Worker Class
# ---------------------------------------------------------------------------

class Worker:
    """
    Async worker unit that fetches jobs from the Scheduler, executes them,
    and reports outcomes.
    """

    def __init__(
        self,
        worker_id: Optional[str] = None,
        job_timeout_seconds: float = 30.0,
        job_handler: Optional[Callable[[AnalysisJob], Awaitable[None]]] = None,
    ) -> None:
        self.worker_id: str = worker_id or f"worker-{uuid.uuid4().hex[:8]}"
        self.context: WorkerContext = WorkerContext(
            worker_id=self.worker_id,
            job_timeout_seconds=job_timeout_seconds,
        )
        self.metrics: WorkerMetrics = WorkerMetrics(worker_id=self.worker_id)
        self.state: WorkerState = WorkerState.IDLE
        self.current_job_id: Optional[str] = None
        self._job_handler = job_handler or self._default_placeholder_handler
        self._task: Optional[asyncio.Task] = None
        self._stop_event: asyncio.Event = asyncio.Event()

    @staticmethod
    async def _default_placeholder_handler(job: AnalysisJob) -> None:
        """Placeholder handler simulating job work when no parser is attached."""
        await asyncio.sleep(0.01)

    def heartbeat(self) -> None:
        """Update worker heartbeat timestamp."""
        self.metrics.last_heartbeat = datetime.now(timezone.utc)

    async def run(self, scheduler: Scheduler) -> None:
        """
        Main worker execution loop.
        Continuously polls scheduler for jobs until stop signal received.
        """
        self.state = WorkerState.IDLE
        logger.debug(f"[Worker:{self.worker_id}] Started worker loop")

        while not self._stop_event.is_set():
            self.heartbeat()

            # Attempt to fetch next job from scheduler
            try:
                job = scheduler.next_job()
            except Exception as exc:
                logger.error(f"[Worker:{self.worker_id}] Error fetching job from scheduler: {exc}")
                await asyncio.sleep(0.05)
                continue

            if job is None:
                # No queued jobs available; yield control briefly
                await asyncio.sleep(0.05)
                continue

            # Assign job to worker
            self.current_job_id = job.job_id
            self.state = WorkerState.BUSY
            start_time = time.monotonic()

            try:
                logger.debug(f"[Worker:{self.worker_id}] Processing job '{job.job_id}' ({job.file.path})")

                # Execute job with timeout protection
                await asyncio.wait_for(
                    self._job_handler(job),
                    timeout=self.context.job_timeout_seconds,
                )

                # Job succeeded
                scheduler.mark_completed(job.job_id)
                duration = time.monotonic() - start_time
                self.metrics.jobs_completed += 1
                self.metrics.total_execution_time_seconds += duration
                logger.debug(f"[Worker:{self.worker_id}] Completed job '{job.job_id}' in {duration:.4f}s")

            except asyncio.TimeoutError:
                duration = time.monotonic() - start_time
                self.metrics.jobs_failed += 1
                self.metrics.total_execution_time_seconds += duration
                err_msg = f"Job execution timed out after {self.context.job_timeout_seconds}s"
                logger.warning(f"[Worker:{self.worker_id}] {err_msg} for job '{job.job_id}'")

                updated_job = scheduler.mark_failed(job.job_id, err_msg)
                if updated_job.is_retryable:
                    try:
                        scheduler.retry(job.job_id)
                        self.metrics.jobs_retried += 1
                    except Exception as retry_exc:
                        logger.error(f"[Worker:{self.worker_id}] Retry failed for job '{job.job_id}': {retry_exc}")

            except asyncio.CancelledError:
                duration = time.monotonic() - start_time
                self.metrics.jobs_cancelled += 1
                self.metrics.total_execution_time_seconds += duration
                logger.info(f"[Worker:{self.worker_id}] Job '{job.job_id}' cancelled")
                try:
                    scheduler.cancel(job.job_id)
                except Exception:
                    pass
                raise  # Re-raise CancelledError to allow worker task clean cancellation if stopping

            except Exception as exc:
                # Error isolation: Worker catches uncaught handler exceptions without dying!
                duration = time.monotonic() - start_time
                self.metrics.jobs_failed += 1
                self.metrics.total_execution_time_seconds += duration
                err_msg = f"Uncaught handler exception: {exc}"
                logger.error(f"[Worker:{self.worker_id}] {err_msg} on job '{job.job_id}'", exc_info=True)

                try:
                    updated_job = scheduler.mark_failed(job.job_id, err_msg)
                    if updated_job.is_retryable:
                        scheduler.retry(job.job_id)
                        self.metrics.jobs_retried += 1
                except Exception as scheduler_exc:
                    logger.error(f"[Worker:{self.worker_id}] Failed updating scheduler for job '{job.job_id}': {scheduler_exc}")

            finally:
                self.current_job_id = None
                if not self._stop_event.is_set():
                    self.state = WorkerState.IDLE

        self.state = WorkerState.STOPPED
        logger.debug(f"[Worker:{self.worker_id}] Worker loop stopped")

    def request_stop(self) -> None:
        """Signal the worker to stop processing new jobs after completing its current job."""
        self.state = WorkerState.STOPPING
        self._stop_event.set()


# ---------------------------------------------------------------------------
# WorkerPool Manager Class
# ---------------------------------------------------------------------------

class WorkerPool:
    """
    Manager for orchestrating a dynamic pool of async Worker instances.
    """

    def __init__(
        self,
        worker_count: int = 4,
        job_timeout_seconds: float = 30.0,
        job_handler: Optional[Callable[[AnalysisJob], Awaitable[None]]] = None,
    ) -> None:
        if worker_count < 1 or worker_count > 128:
            raise WorkerError(
                f"worker_count must be between 1 and 128 (got {worker_count}).",
                code=ErrorCode.WORKER_LIMIT_EXCEEDED,
            )

        self._desired_count: int = worker_count
        self.job_timeout_seconds: float = job_timeout_seconds
        self.job_handler: Optional[Callable[[AnalysisJob], Awaitable[None]]] = job_handler
        self._workers: Dict[str, Worker] = {}
        self._tasks: Dict[str, asyncio.Task] = {}
        self._scheduler: Optional[Scheduler] = None
        self._is_running: bool = False

        for _ in range(self._desired_count):
            worker = Worker(
                job_timeout_seconds=self.job_timeout_seconds,
                job_handler=self.job_handler,
            )
            self._workers[worker.worker_id] = worker

    @property
    def worker_count(self) -> int:
        """Current number of workers in the pool."""
        return len(self._workers)

    @property
    def workers(self) -> List[Worker]:
        """List of active workers in the pool."""
        return list(self._workers.values())

    @property
    def is_running(self) -> bool:
        """True if worker pool has been started."""
        return self._is_running

    def get_worker(self, worker_id: str) -> Optional[Worker]:
        """Retrieve a Worker instance by ID."""
        return self._workers.get(worker_id)

    async def start(self, scheduler: Scheduler) -> None:
        """Start the worker pool with the specified scheduler."""
        if self._is_running:
            return

        self._scheduler = scheduler
        self._is_running = True

        for worker in self._workers.values():
            task = asyncio.create_task(worker.run(self._scheduler), name=f"WorkerTask-{worker.worker_id}")
            worker._task = task
            self._tasks[worker.worker_id] = task

        logger.info(f"[WorkerPool] Started worker pool with {self.worker_count} workers.")

    async def add_worker(self) -> Worker:
        """Dynamically scale up: Create and start a new worker in the pool."""
        if self._scheduler is None and self._is_running:
            raise WorkerError("Cannot add worker: Scheduler not bound to pool.", code=ErrorCode.WORKER_CRASH)

        worker = Worker(
            job_timeout_seconds=self.job_timeout_seconds,
            job_handler=self.job_handler,
        )
        self._workers[worker.worker_id] = worker

        if self._is_running and self._scheduler is not None:
            task = asyncio.create_task(worker.run(self._scheduler), name=f"WorkerTask-{worker.worker_id}")
            worker._task = task
            self._tasks[worker.worker_id] = task

        logger.debug(f"[WorkerPool] Added worker '{worker.worker_id}' (Total: {self.worker_count})")
        return worker

    async def remove_worker(self, worker_id: Optional[str] = None) -> Optional[Worker]:
        """Dynamically scale down: Remove a worker from the pool."""
        if not self._workers:
            return None

        target_id = worker_id
        if target_id is None:
            # Pick an IDLE worker if possible, or any worker
            idle_workers = [w for w in self._workers.values() if w.state == WorkerState.IDLE]
            target_id = idle_workers[0].worker_id if idle_workers else list(self._workers.keys())[-1]

        worker = self._workers.pop(target_id, None)
        if not worker:
            return None

        worker.request_stop()
        task = self._tasks.pop(target_id, None)
        if task and not task.done():
            task.cancel()
            try:
                await task
            except (asyncio.CancelledError, Exception):
                pass

        logger.debug(f"[WorkerPool] Removed worker '{target_id}' (Total: {self.worker_count})")
        return worker

    async def scale(self, new_worker_count: int) -> None:
        """Dynamically resize the worker pool to `new_worker_count`."""
        if new_worker_count < 1 or new_worker_count > 128:
            raise WorkerError(
                f"Target worker_count must be between 1 and 128 (got {new_worker_count}).",
                code=ErrorCode.WORKER_LIMIT_EXCEEDED,
            )

        current = self.worker_count
        if new_worker_count > current:
            for _ in range(new_worker_count - current):
                await self.add_worker()
        elif new_worker_count < current:
            for _ in range(current - new_worker_count):
                await self.remove_worker()

        self._desired_count = new_worker_count
        logger.info(f"[WorkerPool] Scaled worker pool from {current} to {self.worker_count} workers.")

    async def stop(self, graceful: bool = True, timeout: float = 5.0) -> None:
        """Stop all workers in the pool gracefully or forcefully."""
        if not self._is_running:
            return

        logger.info(f"[WorkerPool] Stopping worker pool ({'graceful' if graceful else 'forceful'})...")
        self._is_running = False

        # Request all workers stop
        for worker in self._workers.values():
            worker.request_stop()

        if graceful and self._tasks:
            # Wait for tasks to finish up to timeout
            try:
                await asyncio.wait_for(
                    asyncio.gather(*self._tasks.values(), return_exceptions=True),
                    timeout=timeout,
                )
            except asyncio.TimeoutError:
                logger.warning(f"[WorkerPool] Graceful stop timed out after {timeout}s; forcing cancellation.")
                for task in self._tasks.values():
                    if not task.done():
                        task.cancel()

        else:
            # Force cancel immediately
            for task in self._tasks.values():
                if not task.done():
                    task.cancel()

        self._tasks.clear()
        self._workers.clear()
        logger.info("[WorkerPool] Worker pool stopped.")

    def aggregate_metrics(self) -> Dict[str, Any]:
        """Collect aggregate statistics across all workers in the pool."""
        total_completed = sum(w.metrics.jobs_completed for w in self._workers.values())
        total_failed = sum(w.metrics.jobs_failed for w in self._workers.values())
        total_retried = sum(w.metrics.jobs_retried for w in self._workers.values())
        total_cancelled = sum(w.metrics.jobs_cancelled for w in self._workers.values())
        total_exec_time = sum(w.metrics.total_execution_time_seconds for w in self._workers.values())

        return {
            "worker_count": self.worker_count,
            "jobs_completed": total_completed,
            "jobs_failed": total_failed,
            "jobs_retried": total_retried,
            "jobs_cancelled": total_cancelled,
            "total_execution_time_seconds": round(total_exec_time, 4),
            "worker_details": [w.metrics.to_dict() for w in self._workers.values()],
        }

    def health_check(self, stale_threshold_seconds: float = 10.0) -> Dict[str, Any]:
        """
        Check health of all workers by evaluating last heartbeat timestamp.
        """
        now = datetime.now(timezone.utc)
        healthy = True
        stale_workers: List[str] = []

        for worker in self._workers.values():
            elapsed = (now - worker.metrics.last_heartbeat).total_seconds()
            if elapsed > stale_threshold_seconds:
                healthy = False
                stale_workers.append(worker.worker_id)

        return {
            "healthy": healthy,
            "total_workers": self.worker_count,
            "stale_worker_count": len(stale_workers),
            "stale_workers": stale_workers,
            "active_states": {w.worker_id: w.state.value for w in self._workers.values()},
        }
