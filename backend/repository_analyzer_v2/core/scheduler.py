"""
core/scheduler.py
-----------------
Phase 2.2 — Analysis Job Scheduler.

Manages the lifecycle of AnalysisJob objects from submission through
completion, failure, retry, and cancellation.

Architecture
~~~~~~~~~~~~
The scheduler is implemented as a **thread-safe in-process priority queue**.
A single ``threading.Lock`` guards every mutation.  Reads that only need an
atomic snapshot (e.g. ``progress()``, ``statistics()``) also acquire the lock
so observers see a consistent view.

Priority Queue Implementation
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
``heapq`` provides O(log n) push and O(log n) pop.  A tie-breaking sequence
counter (``_seq``) ensures strict FIFO within the same priority level, which
is required by the spec.  The queue stores ``(negated_priority, seq, job_id)``
tuples so that Python's min-heap gives us the highest-priority job first.

Entry invalidation
~~~~~~~~~~~~~~~~~~
Cancellations and retries do not physically remove items from the heap (which
would be O(n)).  Instead a ``_cancelled_ids`` set and a ``_jobs`` dict act as
the source of truth.  ``next_job()`` skips heap entries whose ``job_id`` is no
longer in ``_jobs`` or whose status is not QUEUED.

This is the standard "lazy deletion" pattern used in production schedulers
(Kubernetes, Celery) to avoid O(n) removal from heaps.

Public API
~~~~~~~~~~
- ``submit(job)``                – enqueue a single job
- ``submit_many(jobs)``          – enqueue a batch (holds lock once)
- ``next_job()``                 – dequeue the highest-priority pending job
- ``retry(job_id)``              – re-enqueue a failed job if retries remain
- ``cancel(job_id)``             – cancel a pending or queued job
- ``mark_completed(job_id)``     – transition running → completed
- ``mark_failed(job_id, error)`` – transition running → failed/retrying
- ``skip(job_id)``               – mark a job as skipped without running it
- ``progress()``                 – returns a ``SchedulerProgress`` snapshot
- ``statistics()``               – returns a ``SchedulerStatistics`` snapshot
"""

from __future__ import annotations

import heapq
import logging
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, Iterable, List, Optional, Set

from models.job import AnalysisJob, JobPriority, JobStatus, TERMINAL_STATUSES
from utils.exceptions import ErrorCode, SchedulerError

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Progress & Statistics data classes
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class SchedulerProgress:
    """
    Immutable snapshot of current scheduler progress.

    Fields are counts of jobs in each lifecycle state at the instant the
    snapshot was taken.  No locking is needed after construction.
    """
    total: int
    pending: int
    queued: int
    running: int
    completed: int
    failed: int
    skipped: int
    cancelled: int
    retrying: int

    @property
    def done(self) -> int:
        """Total terminal jobs (completed + failed + skipped + cancelled)."""
        return self.completed + self.failed + self.skipped + self.cancelled

    @property
    def completion_pct(self) -> float:
        """Percentage of jobs that have reached a terminal state (0–100)."""
        if self.total == 0:
            return 0.0
        return round(self.done / self.total * 100, 2)

    @property
    def success_rate(self) -> float:
        """Percentage of terminal jobs that completed successfully (0–100)."""
        if self.done == 0:
            return 0.0
        return round(self.completed / self.done * 100, 2)


@dataclass(frozen=True)
class SchedulerStatistics:
    """
    Immutable operational statistics snapshot.

    Includes queue depth, retry counts, throughput, and elapsed wall time.
    """
    queue_depth: int
    """Number of jobs currently in QUEUED state awaiting a worker."""

    total_submitted: int
    """Cumulative count of jobs ever submitted to this scheduler instance."""

    total_retries: int
    """Cumulative retry-attempt counter across all jobs."""

    total_errors: int
    """Cumulative count of FAILED transitions (includes eventual successes after retry)."""

    average_duration_seconds: Optional[float]
    """Mean wall-clock duration of COMPLETED jobs (None if none have completed)."""

    elapsed_seconds: float
    """Wall-clock seconds since the scheduler was constructed."""

    language_distribution: Dict[str, int]
    """Job count per language across all submitted jobs."""


# ---------------------------------------------------------------------------
# _QueueEntry
# ---------------------------------------------------------------------------

@dataclass(order=True)
class _QueueEntry:
    """
    Internal heap tuple.

    ``heapq`` is a *min*-heap, so we negate the priority value to turn it into
    a *max*-heap (higher priority → lower heap key → dequeued first).
    ``seq`` provides FIFO ordering within the same priority level.
    ``job_id`` is stored to identify the job without embedding the full object
    in the heap, keeping heap operations cache-friendly.
    """
    neg_priority: int          # -JobPriority.value
    seq: int                   # monotonically increasing insertion counter
    job_id: str = field(compare=False)


# ---------------------------------------------------------------------------
# Scheduler
# ---------------------------------------------------------------------------

class Scheduler:
    """
    Thread-safe, priority-ordered Analysis Job Scheduler.

    Designed to handle tens of thousands of AnalysisJob objects efficiently
    using a heap-backed priority queue with lazy deletion.

    Thread safety
    ~~~~~~~~~~~~~
    A single ``threading.Lock`` serialises all mutations.  Read-only snapshots
    (``progress``, ``statistics``) also acquire the lock to ensure a consistent
    view.  Callers **must not** hold the lock themselves.

    Usage::

        scheduler = Scheduler()

        jobs = [
            AnalysisJob.from_repository_file(repo_id, f)
            for f in discovered_files
        ]
        scheduler.submit_many(jobs)

        while (job := scheduler.next_job()) is not None:
            try:
                result = worker.process(job)
                scheduler.mark_completed(job.job_id)
            except Exception as exc:
                scheduler.mark_failed(job.job_id, str(exc))

        print(scheduler.progress())
    """

    def __init__(self) -> None:
        self._lock: threading.Lock = threading.Lock()

        # Source of truth: job_id → AnalysisJob
        self._jobs: Dict[str, AnalysisJob] = {}

        # Heap of _QueueEntry objects
        self._heap: List[_QueueEntry] = []

        # Set of job_ids that have been dequeued or cancelled (for lazy deletion)
        self._dequeued_ids: Set[str] = set()

        # Monotonic sequence counter for FIFO within equal priority
        self._seq: int = 0

        # Cumulative counters (never decremented)
        self._total_submitted: int = 0
        self._total_retries: int = 0
        self._total_errors: int = 0

        # For throughput / duration tracking
        self._created_at: float = time.monotonic()
        self._completed_durations: List[float] = []

        logger.debug("[Scheduler] Initialised")

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _enqueue(self, job: AnalysisJob) -> None:
        """Push a job onto the heap.  Caller must hold ``self._lock``."""
        entry = _QueueEntry(
            neg_priority=-job.priority.value,
            seq=self._seq,
            job_id=job.job_id,
        )
        self._seq += 1
        heapq.heappush(self._heap, entry)

    def _mutate(self, job_id: str, **updates) -> AnalysisJob:
        """
        Return a new AnalysisJob with the given field updates applied.
        Stores the mutated copy back into ``_jobs``.
        Caller must hold ``self._lock``.
        """
        existing = self._jobs[job_id]
        mutated = existing.model_copy(update=updates)
        self._jobs[job_id] = mutated
        return mutated

    def _require_job(self, job_id: str) -> AnalysisJob:
        """Raise ``SchedulerError`` if the job is not tracked.  Caller holds lock."""
        if job_id not in self._jobs:
            raise SchedulerError(
                f"Job '{job_id}' is not tracked by this scheduler.",
                code=ErrorCode.SCHEDULER_JOB_NOT_FOUND,
            )
        return self._jobs[job_id]

    def _require_status(self, job: AnalysisJob, *allowed: JobStatus) -> None:
        """Raise ``SchedulerError`` if the job is not in one of ``allowed`` statuses."""
        if job.status not in allowed:
            raise SchedulerError(
                f"Job '{job.job_id}' is in status '{job.status.value}', "
                f"but expected one of: {[s.value for s in allowed]}.",
                code=ErrorCode.SCHEDULER_INVALID_TRANSITION,
            )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def submit(self, job: AnalysisJob) -> None:
        """
        Submit a single AnalysisJob to the queue.

        The job must be in PENDING or QUEUED status.  Its status is
        transitioned to QUEUED on admission.

        :param job: The AnalysisJob to enqueue.
        :raises SchedulerError: If a job with the same ``job_id`` was already submitted.
        :raises SchedulerError: If the job is not in a submittable state.
        """
        with self._lock:
            if job.job_id in self._jobs:
                raise SchedulerError(
                    f"Job '{job.job_id}' has already been submitted.",
                    code=ErrorCode.SCHEDULER_DUPLICATE_JOB,
                )
            self._require_status(job, JobStatus.PENDING, JobStatus.QUEUED)

            queued_job = job.model_copy(update={"status": JobStatus.QUEUED})
            self._jobs[queued_job.job_id] = queued_job
            self._enqueue(queued_job)
            self._total_submitted += 1

        logger.debug(
            f"[Scheduler] Submitted job '{job.job_id}' "
            f"(lang={job.language}, priority={job.priority.name})"
        )

    def submit_many(self, jobs: Iterable[AnalysisJob]) -> int:
        """
        Submit an iterable of AnalysisJob objects atomically under one lock acquisition.

        :param jobs: Iterable of AnalysisJob objects in PENDING or QUEUED state.
        :return: Number of jobs successfully admitted.
        :raises SchedulerError: If any duplicate job_id is detected (partial rollback
                                does NOT occur; already-admitted jobs remain in the queue).
        """
        job_list = list(jobs)
        admitted = 0

        with self._lock:
            for job in job_list:
                if job.job_id in self._jobs:
                    raise SchedulerError(
                        f"Duplicate job_id '{job.job_id}' in submit_many batch.",
                        code=ErrorCode.SCHEDULER_DUPLICATE_JOB,
                    )
                self._require_status(job, JobStatus.PENDING, JobStatus.QUEUED)

                queued_job = job.model_copy(update={"status": JobStatus.QUEUED})
                self._jobs[queued_job.job_id] = queued_job
                self._enqueue(queued_job)
                self._total_submitted += 1
                admitted += 1

        logger.info(f"[Scheduler] Batch submitted {admitted} job(s)")
        return admitted

    def next_job(self) -> Optional[AnalysisJob]:
        """
        Dequeue and return the highest-priority QUEUED job.

        Uses lazy deletion: heap entries for cancelled or already-claimed jobs
        are skipped until a live QUEUED job is found.

        :return: The next AnalysisJob transitioned to RUNNING, or ``None`` if
                 the queue is empty.
        """
        with self._lock:
            while self._heap:
                entry = heapq.heappop(self._heap)
                job_id = entry.job_id

                # Lazy deletion: skip if job was cancelled or already claimed
                if job_id not in self._jobs:
                    continue
                job = self._jobs[job_id]
                if job.status != JobStatus.QUEUED:
                    continue

                # Transition to RUNNING — worker_id placeholder "scheduler-assigned"
                # will be replaced by the actual worker when it claims the job.
                running_job = job.model_copy(update={
                    "status": JobStatus.RUNNING,
                    "started_at": datetime.now(timezone.utc),
                    "worker_id": "scheduler-assigned",
                })
                self._jobs[job_id] = running_job
                self._dequeued_ids.add(job_id)

                logger.debug(
                    f"[Scheduler] Dispatched job '{job_id}' "
                    f"(lang={running_job.language}, priority={running_job.priority.name})"
                )
                return running_job

        return None

    def retry(self, job_id: str) -> AnalysisJob:
        """
        Re-enqueue a failed job for another attempt.

        Increments ``retry_count``, resets status to QUEUED, and clears
        ``worker_id``, ``started_at``, ``finished_at``, and ``error``.

        :param job_id: ID of the job to retry.
        :return: The updated AnalysisJob in QUEUED state.
        :raises SchedulerError: If the job is not tracked, is not retryable, or
                                has exhausted ``max_retries``.
        """
        with self._lock:
            job = self._require_job(job_id)
            self._require_status(job, JobStatus.FAILED, JobStatus.RETRYING)

            if job.retry_count >= job.max_retries:
                raise SchedulerError(
                    f"Job '{job_id}' has exhausted its retry budget "
                    f"({job.retry_count}/{job.max_retries}).",
                    code=ErrorCode.SCHEDULER_RETRY_EXHAUSTED,
                )

            retried_job = job.model_copy(update={
                "status": JobStatus.QUEUED,
                "retry_count": job.retry_count + 1,
                "worker_id": None,
                "started_at": None,
                "finished_at": None,
                "error": None,
            })
            self._jobs[job_id] = retried_job
            # Remove from dequeued set so next_job() can claim it again
            self._dequeued_ids.discard(job_id)
            self._enqueue(retried_job)
            self._total_retries += 1

        logger.info(
            f"[Scheduler] Retrying job '{job_id}' "
            f"(attempt {retried_job.retry_count}/{retried_job.max_retries})"
        )
        return retried_job

    def cancel(self, job_id: str) -> AnalysisJob:
        """
        Cancel a job that is in PENDING, QUEUED, or RUNNING state.

        Cancelled jobs remain in ``_jobs`` for audit purposes but are
        removed from the dispatch path via lazy deletion.

        :param job_id: ID of the job to cancel.
        :return: The updated AnalysisJob in CANCELLED state.
        :raises SchedulerError: If the job is already in a terminal state.
        """
        with self._lock:
            job = self._require_job(job_id)
            if job.status in TERMINAL_STATUSES:
                raise SchedulerError(
                    f"Job '{job_id}' is already in terminal state '{job.status.value}' "
                    f"and cannot be cancelled.",
                    code=ErrorCode.SCHEDULER_INVALID_TRANSITION,
                )

            now = datetime.now(timezone.utc)
            cancelled_job = job.model_copy(update={
                "status": JobStatus.CANCELLED,
                "finished_at": now if job.started_at is not None else None,
            })
            self._jobs[job_id] = cancelled_job
            # Add to dequeued set so heap entries are skipped by next_job()
            self._dequeued_ids.add(job_id)

        logger.info(f"[Scheduler] Cancelled job '{job_id}'")
        return cancelled_job

    def mark_completed(self, job_id: str) -> AnalysisJob:
        """
        Mark a RUNNING job as successfully completed.

        :param job_id: ID of the job to complete.
        :return: The updated AnalysisJob in COMPLETED state.
        :raises SchedulerError: If the job is not in RUNNING state.
        """
        with self._lock:
            job = self._require_job(job_id)
            self._require_status(job, JobStatus.RUNNING)

            finished = datetime.now(timezone.utc)
            completed_job = job.model_copy(update={
                "status": JobStatus.COMPLETED,
                "finished_at": finished,
            })
            self._jobs[job_id] = completed_job

            # Track duration for statistics
            if completed_job.started_at is not None:
                duration = (finished - completed_job.started_at).total_seconds()
                self._completed_durations.append(duration)

        logger.debug(f"[Scheduler] Completed job '{job_id}'")
        return completed_job

    def mark_failed(self, job_id: str, error: str) -> AnalysisJob:
        """
        Mark a RUNNING job as failed.

        If ``retry_count < max_retries``, status is set to RETRYING; otherwise
        FAILED.  The caller should subsequently call ``retry()`` if RETRYING.

        :param job_id: ID of the job that failed.
        :param error: Human-readable description of the failure.
        :return: The updated AnalysisJob in FAILED or RETRYING state.
        :raises SchedulerError: If the job is not in RUNNING state.
        """
        with self._lock:
            job = self._require_job(job_id)
            self._require_status(job, JobStatus.RUNNING)

            finished = datetime.now(timezone.utc)
            new_status = (
                JobStatus.RETRYING
                if job.retry_count < job.max_retries
                else JobStatus.FAILED
            )
            failed_job = job.model_copy(update={
                "status": new_status,
                "finished_at": finished,
                "error": error,
            })
            self._jobs[job_id] = failed_job
            self._total_errors += 1

        logger.warning(
            f"[Scheduler] Job '{job_id}' transitioned to {new_status.value}: {error}"
        )
        return failed_job

    def skip(self, job_id: str, reason: Optional[str] = None) -> AnalysisJob:
        """
        Mark a PENDING, QUEUED, or RUNNING job as skipped.

        Skipping is appropriate when no plugin supports the file's language or
        the file fails a pre-processing gate check.

        :param job_id: ID of the job to skip.
        :param reason: Optional human-readable reason stored in ``error`` field.
        :return: The updated AnalysisJob in SKIPPED state.
        :raises SchedulerError: If the job is already in a terminal state.
        """
        with self._lock:
            job = self._require_job(job_id)
            if job.status in TERMINAL_STATUSES:
                raise SchedulerError(
                    f"Job '{job_id}' is already terminal ('{job.status.value}') "
                    f"and cannot be skipped.",
                    code=ErrorCode.SCHEDULER_INVALID_TRANSITION,
                )

            now = datetime.now(timezone.utc)
            skipped_job = job.model_copy(update={
                "status": JobStatus.SKIPPED,
                "finished_at": now if job.started_at is not None else None,
                "error": reason,
            })
            self._jobs[job_id] = skipped_job
            self._dequeued_ids.add(job_id)

        logger.debug(f"[Scheduler] Skipped job '{job_id}': {reason or 'no reason given'}")
        return skipped_job

    def progress(self) -> SchedulerProgress:
        """
        Return an immutable snapshot of job lifecycle counts.

        Acquires the lock to ensure a consistent read.

        :return: ``SchedulerProgress`` dataclass instance.
        """
        counts: Dict[JobStatus, int] = {s: 0 for s in JobStatus}
        with self._lock:
            for job in self._jobs.values():
                counts[job.status] += 1
            total = len(self._jobs)

        return SchedulerProgress(
            total=total,
            pending=counts[JobStatus.PENDING],
            queued=counts[JobStatus.QUEUED],
            running=counts[JobStatus.RUNNING],
            completed=counts[JobStatus.COMPLETED],
            failed=counts[JobStatus.FAILED],
            skipped=counts[JobStatus.SKIPPED],
            cancelled=counts[JobStatus.CANCELLED],
            retrying=counts[JobStatus.RETRYING],
        )

    def statistics(self) -> SchedulerStatistics:
        """
        Return an immutable snapshot of operational scheduler statistics.

        :return: ``SchedulerStatistics`` dataclass instance.
        """
        with self._lock:
            queue_depth = sum(
                1 for j in self._jobs.values()
                if j.status == JobStatus.QUEUED
            )
            durations = list(self._completed_durations)
            total_submitted = self._total_submitted
            total_retries = self._total_retries
            total_errors = self._total_errors

            lang_dist: Dict[str, int] = {}
            for job in self._jobs.values():
                lang_dist[job.language] = lang_dist.get(job.language, 0) + 1

        avg_duration = (
            sum(durations) / len(durations) if durations else None
        )
        elapsed = time.monotonic() - self._created_at

        return SchedulerStatistics(
            queue_depth=queue_depth,
            total_submitted=total_submitted,
            total_retries=total_retries,
            total_errors=total_errors,
            average_duration_seconds=avg_duration,
            elapsed_seconds=elapsed,
            language_distribution=lang_dist,
        )

    def get_job(self, job_id: str) -> Optional[AnalysisJob]:
        """
        Return the current state of a tracked job, or ``None`` if not found.

        :param job_id: ID of the job to retrieve.
        :return: Current ``AnalysisJob`` snapshot or ``None``.
        """
        with self._lock:
            return self._jobs.get(job_id)

    def all_jobs(self) -> List[AnalysisJob]:
        """
        Return a snapshot list of all tracked jobs in their current state.

        :return: List of ``AnalysisJob`` instances (order is unspecified).
        """
        with self._lock:
            return list(self._jobs.values())

    def pending_count(self) -> int:
        """Return the number of jobs awaiting dispatch (QUEUED state)."""
        with self._lock:
            return sum(1 for j in self._jobs.values() if j.status == JobStatus.QUEUED)

    def is_idle(self) -> bool:
        """
        Return True if no jobs are queued or running.

        Useful as a completion sentinel in single-process scenarios.
        """
        with self._lock:
            return not any(
                j.status in {JobStatus.QUEUED, JobStatus.RUNNING}
                for j in self._jobs.values()
            )
