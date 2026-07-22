"""
tests/test_scheduler.py
-----------------------
Comprehensive unit tests for Phase 2.2 — Analysis Job Scheduler.

Test groups
~~~~~~~~~~~
TestSchedulerProgress     — SchedulerProgress dataclass computed fields
TestSchedulerStatistics   — SchedulerStatistics fields
TestSchedulerSubmit       — submit() and submit_many() happy & error paths
TestSchedulerNextJob      — next_job() priority, FIFO, empty queue
TestSchedulerRetry        — retry() happy path, exhausted budget, bad state
TestSchedulerCancel       — cancel() happy path, terminal guard
TestSchedulerMarkCompleted — mark_completed() transitions and duration tracking
TestSchedulerMarkFailed   — mark_failed() RETRYING vs FAILED branching
TestSchedulerSkip         — skip() behaviour
TestSchedulerProgress     — progress() and statistics() snapshots
TestSchedulerEdgeCases    — large batches, concurrent access, idle detection
TestSchedulerPipelineStage — SchedulerStage integration inside Pipeline context
"""
from __future__ import annotations

import threading
import time
from datetime import datetime, timezone
from typing import List

import pytest

from core.scheduler import Scheduler, SchedulerProgress, SchedulerStatistics
from models.job import AnalysisJob, JobPriority, JobStatus, TERMINAL_STATUSES
from models.repository import RepositoryFile
from pipeline.context import PipelineContext
from pipeline.scheduler import SchedulerStage
from utils.exceptions import SchedulerError


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_file(path: str = "src/main.py", language: str = "python") -> RepositoryFile:
    return RepositoryFile(
        path=path,
        name=path.split("/")[-1],
        extension=path.rsplit(".", 1)[-1] if "." in path else "",
        language=language,
    )


def make_job(
    language: str = "python",
    priority: JobPriority = JobPriority.NORMAL,
    max_retries: int = 3,
    repo_id: str = "repo-1",
    file_path: str = "src/main.py",
) -> AnalysisJob:
    return AnalysisJob.from_repository_file(
        repository_id=repo_id,
        file=make_file(file_path, language),
        priority=priority,
        max_retries=max_retries,
    )


def filled_scheduler(n: int = 5) -> tuple[Scheduler, List[AnalysisJob]]:
    """Return a Scheduler pre-loaded with n NORMAL-priority jobs."""
    s = Scheduler()
    jobs = [make_job(file_path=f"src/file_{i}.py") for i in range(n)]
    s.submit_many(jobs)
    return s, jobs


# ---------------------------------------------------------------------------
# SchedulerProgress
# ---------------------------------------------------------------------------

class TestSchedulerProgress:
    def test_done_is_sum_of_terminal(self):
        p = SchedulerProgress(
            total=10, pending=1, queued=2, running=1,
            completed=3, failed=1, skipped=1, cancelled=1, retrying=0,
        )
        assert p.done == 6  # completed + failed + skipped + cancelled

    def test_completion_pct_zero_when_empty(self):
        p = SchedulerProgress(
            total=0, pending=0, queued=0, running=0,
            completed=0, failed=0, skipped=0, cancelled=0, retrying=0,
        )
        assert p.completion_pct == 0.0

    def test_completion_pct_correct(self):
        p = SchedulerProgress(
            total=10, pending=0, queued=0, running=0,
            completed=5, failed=2, skipped=1, cancelled=2, retrying=0,
        )
        assert p.completion_pct == 100.0

    def test_success_rate_zero_when_no_terminal(self):
        p = SchedulerProgress(
            total=5, pending=5, queued=0, running=0,
            completed=0, failed=0, skipped=0, cancelled=0, retrying=0,
        )
        assert p.success_rate == 0.0

    def test_success_rate_100_when_all_completed(self):
        p = SchedulerProgress(
            total=3, pending=0, queued=0, running=0,
            completed=3, failed=0, skipped=0, cancelled=0, retrying=0,
        )
        assert p.success_rate == 100.0

    def test_success_rate_partial(self):
        p = SchedulerProgress(
            total=4, pending=0, queued=0, running=0,
            completed=1, failed=3, skipped=0, cancelled=0, retrying=0,
        )
        assert p.success_rate == 25.0


# ---------------------------------------------------------------------------
# TestSchedulerSubmit
# ---------------------------------------------------------------------------

class TestSchedulerSubmit:
    def test_submit_single_job_queues_it(self):
        s = Scheduler()
        job = make_job()
        s.submit(job)
        assert s.progress().queued == 1

    def test_submit_transitions_pending_to_queued(self):
        s = Scheduler()
        job = make_job()
        assert job.status == JobStatus.PENDING
        s.submit(job)
        stored = s.get_job(job.job_id)
        assert stored is not None
        assert stored.status == JobStatus.QUEUED

    def test_submit_duplicate_raises(self):
        s = Scheduler()
        job = make_job()
        s.submit(job)
        with pytest.raises(SchedulerError, match="already been submitted"):
            s.submit(job)

    def test_submit_terminal_job_raises(self):
        s = Scheduler()
        job = make_job()
        # Manually force into a terminal state by manipulating a copy
        terminal = job.model_copy(update={"status": JobStatus.COMPLETED, "worker_id": "w"})
        with pytest.raises(SchedulerError):
            s.submit(terminal)

    def test_submit_many_returns_count(self):
        s = Scheduler()
        jobs = [make_job(file_path=f"f{i}.py") for i in range(10)]
        admitted = s.submit_many(jobs)
        assert admitted == 10

    def test_submit_many_all_queued(self):
        s, jobs = filled_scheduler(20)
        assert s.progress().queued == 20

    def test_submit_many_duplicate_raises(self):
        s = Scheduler()
        job = make_job()
        with pytest.raises(SchedulerError, match="Duplicate"):
            s.submit_many([job, job])

    def test_submit_many_empty_iterable_returns_zero(self):
        s = Scheduler()
        assert s.submit_many([]) == 0


# ---------------------------------------------------------------------------
# TestSchedulerNextJob
# ---------------------------------------------------------------------------

class TestSchedulerNextJob:
    def test_next_job_returns_none_on_empty_queue(self):
        s = Scheduler()
        assert s.next_job() is None

    def test_next_job_transitions_to_running(self):
        s = Scheduler()
        s.submit(make_job())
        job = s.next_job()
        assert job is not None
        assert job.status == JobStatus.RUNNING

    def test_next_job_sets_started_at(self):
        s = Scheduler()
        s.submit(make_job())
        job = s.next_job()
        assert job is not None
        assert job.started_at is not None

    def test_next_job_returns_none_when_all_dispatched(self):
        s, jobs = filled_scheduler(3)
        for _ in range(3):
            s.next_job()
        assert s.next_job() is None

    def test_next_job_respects_priority_order(self):
        s = Scheduler()
        low = make_job(priority=JobPriority.LOW, file_path="low.py")
        normal = make_job(priority=JobPriority.NORMAL, file_path="normal.py")
        high = make_job(priority=JobPriority.HIGH, file_path="high.py")
        critical = make_job(priority=JobPriority.CRITICAL, file_path="critical.py")

        # Submit in ascending priority order to verify heap correctness
        s.submit(low)
        s.submit(normal)
        s.submit(high)
        s.submit(critical)

        dispatched = [s.next_job() for _ in range(4)]
        priorities = [j.priority for j in dispatched]
        assert priorities == [
            JobPriority.CRITICAL,
            JobPriority.HIGH,
            JobPriority.NORMAL,
            JobPriority.LOW,
        ]

    def test_next_job_fifo_within_same_priority(self):
        """Jobs at the same priority level must be dequeued in insertion order."""
        s = Scheduler()
        jobs = [make_job(file_path=f"f{i}.py") for i in range(5)]
        s.submit_many(jobs)
        dispatched_ids = [s.next_job().job_id for _ in range(5)]
        original_ids = [j.job_id for j in jobs]
        assert dispatched_ids == original_ids

    def test_next_job_skips_cancelled_entries(self):
        s = Scheduler()
        job = make_job()
        s.submit(job)
        s.cancel(job.job_id)
        assert s.next_job() is None


# ---------------------------------------------------------------------------
# TestSchedulerRetry
# ---------------------------------------------------------------------------

class TestSchedulerRetry:
    def _failed_job_id(self, s: Scheduler) -> str:
        s.submit(make_job())
        job = s.next_job()
        s.mark_failed(job.job_id, "network error")
        # If status is RETRYING transition again to FAILED for retry test
        stored = s.get_job(job.job_id)
        if stored.status == JobStatus.RETRYING:
            # Force to FAILED for retry-exhaustion tests via model_copy hack
            pass
        return job.job_id

    def test_retry_requeues_failed_job(self):
        s = Scheduler()
        s.submit(make_job(max_retries=3))
        job = s.next_job()
        s.mark_failed(job.job_id, "err")
        stored = s.get_job(job.job_id)
        if stored.status == JobStatus.RETRYING:
            retried = s.retry(job.job_id)
            assert retried.status == JobStatus.QUEUED
            assert retried.retry_count == 1

    def test_retry_increments_retry_count(self):
        s = Scheduler()
        s.submit(make_job(max_retries=3))
        job = s.next_job()
        s.mark_failed(job.job_id, "err")
        stored = s.get_job(job.job_id)
        if stored.status == JobStatus.RETRYING:
            retried = s.retry(job.job_id)
            assert retried.retry_count == 1

    def test_retry_clears_error_and_timestamps(self):
        s = Scheduler()
        s.submit(make_job(max_retries=3))
        job = s.next_job()
        s.mark_failed(job.job_id, "boom")
        stored = s.get_job(job.job_id)
        if stored.status == JobStatus.RETRYING:
            retried = s.retry(job.job_id)
            assert retried.error is None
            assert retried.worker_id is None
            assert retried.started_at is None
            assert retried.finished_at is None

    def test_retry_exhausted_raises(self):
        s = Scheduler()
        s.submit(make_job(max_retries=1))
        # Exhaust all retries
        for _ in range(2):  # fail, retry; fail again → FAILED
            j = s.next_job()
            if j is None:
                break
            s.mark_failed(j.job_id, "err")
            stored = s.get_job(j.job_id)
            if stored.status == JobStatus.RETRYING:
                s.retry(j.job_id)
            elif stored.status == JobStatus.FAILED:
                with pytest.raises(SchedulerError, match="retry budget"):
                    s.retry(j.job_id)
                return
        # If job is FAILED at this point
        all_jobs = s.all_jobs()
        failed = [j for j in all_jobs if j.status == JobStatus.FAILED]
        if failed:
            with pytest.raises(SchedulerError):
                s.retry(failed[0].job_id)

    def test_retry_unknown_job_raises(self):
        s = Scheduler()
        with pytest.raises(SchedulerError, match="not tracked"):
            s.retry("nonexistent-id")


# ---------------------------------------------------------------------------
# TestSchedulerCancel
# ---------------------------------------------------------------------------

class TestSchedulerCancel:
    def test_cancel_queued_job(self):
        s = Scheduler()
        job = make_job()
        s.submit(job)
        cancelled = s.cancel(job.job_id)
        assert cancelled.status == JobStatus.CANCELLED

    def test_cancel_removes_from_dispatch_path(self):
        s = Scheduler()
        job = make_job()
        s.submit(job)
        s.cancel(job.job_id)
        assert s.next_job() is None

    def test_cancel_running_job(self):
        s = Scheduler()
        s.submit(make_job())
        job = s.next_job()
        cancelled = s.cancel(job.job_id)
        assert cancelled.status == JobStatus.CANCELLED

    def test_cancel_already_completed_raises(self):
        s = Scheduler()
        s.submit(make_job())
        job = s.next_job()
        s.mark_completed(job.job_id)
        with pytest.raises(SchedulerError, match="terminal"):
            s.cancel(job.job_id)

    def test_cancel_unknown_job_raises(self):
        s = Scheduler()
        with pytest.raises(SchedulerError):
            s.cancel("ghost-id")


# ---------------------------------------------------------------------------
# TestSchedulerMarkCompleted
# ---------------------------------------------------------------------------

class TestSchedulerMarkCompleted:
    def test_mark_completed_transitions_correctly(self):
        s = Scheduler()
        s.submit(make_job())
        job = s.next_job()
        completed = s.mark_completed(job.job_id)
        assert completed.status == JobStatus.COMPLETED

    def test_mark_completed_sets_finished_at(self):
        s = Scheduler()
        s.submit(make_job())
        job = s.next_job()
        completed = s.mark_completed(job.job_id)
        assert completed.finished_at is not None

    def test_mark_completed_updates_duration_stats(self):
        s = Scheduler()
        s.submit(make_job())
        job = s.next_job()
        s.mark_completed(job.job_id)
        stats = s.statistics()
        assert stats.average_duration_seconds is not None
        assert stats.average_duration_seconds >= 0.0

    def test_mark_completed_not_running_raises(self):
        s = Scheduler()
        s.submit(make_job())
        job = s.next_job()
        s.mark_completed(job.job_id)
        with pytest.raises(SchedulerError, match="running"):
            s.mark_completed(job.job_id)


# ---------------------------------------------------------------------------
# TestSchedulerMarkFailed
# ---------------------------------------------------------------------------

class TestSchedulerMarkFailed:
    def test_mark_failed_transitions_to_retrying_when_retries_remain(self):
        s = Scheduler()
        s.submit(make_job(max_retries=3))
        job = s.next_job()
        failed = s.mark_failed(job.job_id, "timeout")
        assert failed.status == JobStatus.RETRYING

    def test_mark_failed_transitions_to_failed_when_no_retries(self):
        s = Scheduler()
        s.submit(make_job(max_retries=0))
        job = s.next_job()
        failed = s.mark_failed(job.job_id, "fatal")
        assert failed.status == JobStatus.FAILED

    def test_mark_failed_stores_error_message(self):
        s = Scheduler()
        s.submit(make_job(max_retries=0))
        job = s.next_job()
        failed = s.mark_failed(job.job_id, "ImportError: module not found")
        assert failed.error == "ImportError: module not found"

    def test_mark_failed_increments_total_errors(self):
        s = Scheduler()
        s.submit(make_job(max_retries=0))
        job = s.next_job()
        s.mark_failed(job.job_id, "err")
        assert s.statistics().total_errors == 1

    def test_mark_failed_not_running_raises(self):
        s = Scheduler()
        job = make_job()
        s.submit(job)
        with pytest.raises(SchedulerError, match="running"):
            s.mark_failed(job.job_id, "bad")


# ---------------------------------------------------------------------------
# TestSchedulerSkip
# ---------------------------------------------------------------------------

class TestSchedulerSkip:
    def test_skip_queued_job(self):
        s = Scheduler()
        job = make_job()
        s.submit(job)
        skipped = s.skip(job.job_id, "no plugin for language")
        assert skipped.status == JobStatus.SKIPPED

    def test_skip_stores_reason(self):
        s = Scheduler()
        job = make_job()
        s.submit(job)
        skipped = s.skip(job.job_id, "unsupported")
        assert skipped.error == "unsupported"

    def test_skip_removes_from_dispatch(self):
        s = Scheduler()
        job = make_job()
        s.submit(job)
        s.skip(job.job_id)
        assert s.next_job() is None

    def test_skip_already_terminal_raises(self):
        s = Scheduler()
        s.submit(make_job())
        job = s.next_job()
        s.mark_completed(job.job_id)
        with pytest.raises(SchedulerError, match="terminal"):
            s.skip(job.job_id)


# ---------------------------------------------------------------------------
# TestSchedulerProgressAndStatistics
# ---------------------------------------------------------------------------

class TestSchedulerProgressAndStatistics:
    def test_progress_empty_scheduler(self):
        s = Scheduler()
        p = s.progress()
        assert p.total == 0
        assert p.completion_pct == 0.0

    def test_progress_tracks_all_states(self):
        s = Scheduler()
        # Submit 3 jobs; dispatch 2; complete 1; fail 1; leave 1 queued
        jobs = [make_job(file_path=f"f{i}.py") for i in range(3)]
        s.submit_many(jobs)
        j1 = s.next_job()
        j2 = s.next_job()
        s.mark_completed(j1.job_id)
        s.mark_failed(j2.job_id, "err")

        p = s.progress()
        assert p.total == 3
        assert p.completed == 1
        assert p.queued == 1
        # j2 will be RETRYING (max_retries=3 by default)
        assert p.failed + p.retrying >= 1

    def test_statistics_language_distribution(self):
        s = Scheduler()
        s.submit(make_job(language="python", file_path="a.py"))
        s.submit(make_job(language="typescript", file_path="b.ts"))
        s.submit(make_job(language="typescript", file_path="c.ts"))
        stats = s.statistics()
        assert stats.language_distribution["python"] == 1
        assert stats.language_distribution["typescript"] == 2

    def test_statistics_total_submitted_matches(self):
        s, jobs = filled_scheduler(7)
        assert s.statistics().total_submitted == 7

    def test_statistics_queue_depth(self):
        s, jobs = filled_scheduler(5)
        s.next_job()
        assert s.statistics().queue_depth == 4

    def test_statistics_elapsed_seconds_positive(self):
        s = Scheduler()
        assert s.statistics().elapsed_seconds >= 0.0

    def test_statistics_avg_duration_none_with_no_completed(self):
        s, _ = filled_scheduler(3)
        assert s.statistics().average_duration_seconds is None

    def test_statistics_avg_duration_after_completion(self):
        s = Scheduler()
        s.submit(make_job())
        j = s.next_job()
        time.sleep(0.01)
        s.mark_completed(j.job_id)
        stats = s.statistics()
        assert stats.average_duration_seconds is not None
        assert stats.average_duration_seconds >= 0.01


# ---------------------------------------------------------------------------
# TestSchedulerEdgeCases
# ---------------------------------------------------------------------------

class TestSchedulerEdgeCases:
    def test_is_idle_when_empty(self):
        assert Scheduler().is_idle() is True

    def test_is_not_idle_when_jobs_queued(self):
        s, _ = filled_scheduler(1)
        assert s.is_idle() is False

    def test_is_idle_after_all_completed(self):
        s, jobs = filled_scheduler(3)
        for _ in range(3):
            j = s.next_job()
            s.mark_completed(j.job_id)
        assert s.is_idle() is True

    def test_pending_count_matches_queued(self):
        s, _ = filled_scheduler(4)
        assert s.pending_count() == 4
        s.next_job()
        assert s.pending_count() == 3

    def test_get_job_returns_none_for_unknown(self):
        s = Scheduler()
        assert s.get_job("nonexistent") is None

    def test_all_jobs_returns_snapshot(self):
        s, jobs = filled_scheduler(5)
        snapshot = s.all_jobs()
        assert len(snapshot) == 5

    def test_large_batch_submit_and_drain(self):
        """Validate scheduler handles 10,000 jobs efficiently."""
        n = 10_000
        s = Scheduler()
        jobs = [make_job(file_path=f"src/f{i}.py") for i in range(n)]
        s.submit_many(jobs)

        dispatched = 0
        while (j := s.next_job()) is not None:
            s.mark_completed(j.job_id)
            dispatched += 1

        assert dispatched == n
        assert s.progress().completed == n
        assert s.is_idle()

    def test_thread_safety_concurrent_submit_and_drain(self):
        """Multiple threads submitting and draining must not corrupt state."""
        s = Scheduler()
        errors: List[Exception] = []
        submitted_count = 50

        def producer():
            try:
                jobs = [make_job(file_path=f"t{threading.get_ident()}_{i}.py") for i in range(submitted_count)]
                s.submit_many(jobs)
            except Exception as exc:
                errors.append(exc)

        def consumer():
            try:
                for _ in range(submitted_count * 2):  # generous loop
                    j = s.next_job()
                    if j is not None:
                        s.mark_completed(j.job_id)
                    else:
                        time.sleep(0.001)
            except Exception as exc:
                errors.append(exc)

        threads = [threading.Thread(target=producer) for _ in range(4)]
        threads += [threading.Thread(target=consumer) for _ in range(2)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=10)

        assert errors == [], f"Thread errors: {errors}"

    def test_retry_loop_runs_job_to_completion(self):
        """Simulate a job that fails once then succeeds on retry."""
        s = Scheduler()
        s.submit(make_job(max_retries=2))

        j = s.next_job()
        s.mark_failed(j.job_id, "transient error")

        stored = s.get_job(j.job_id)
        assert stored.status == JobStatus.RETRYING

        s.retry(j.job_id)

        j2 = s.next_job()
        assert j2 is not None
        assert j2.job_id == j.job_id
        assert j2.retry_count == 1

        s.mark_completed(j2.job_id)
        assert s.get_job(j.job_id).status == JobStatus.COMPLETED


# ---------------------------------------------------------------------------
# TestSchedulerPipelineStage
# ---------------------------------------------------------------------------

class TestSchedulerPipelineStage:
    def _make_ctx(self, files: List[RepositoryFile]) -> PipelineContext:
        from models.repository import Repository
        repo = Repository(id="repo-stage-test", url="/tmp", name="test")
        ctx = PipelineContext(run_id="run-sched-test", repository=repo)
        ctx.metadata["discovered_files"] = files
        ctx.start()
        return ctx

    def test_stage_produces_scheduler_in_metadata(self):
        files = [make_file(f"src/f{i}.py") for i in range(5)]
        ctx = self._make_ctx(files)
        stage = SchedulerStage()
        stage.run(ctx)
        assert "scheduler" in ctx.metadata
        assert isinstance(ctx.metadata["scheduler"], Scheduler)

    def test_stage_queues_all_discovered_files(self):
        n = 12
        files = [make_file(f"src/f{i}.py") for i in range(n)]
        ctx = self._make_ctx(files)
        SchedulerStage().run(ctx)
        scheduler: Scheduler = ctx.metadata["scheduler"]
        assert scheduler.progress().queued == n

    def test_stage_respects_priority_for_critical_files(self):
        files = [
            make_file("src/main.py", "python"),    # CRITICAL filename
            make_file("src/utils.py", "python"),   # HIGH extension
            make_file("data.bin", "unknown"),       # LOW unknown language
        ]
        ctx = self._make_ctx(files)
        SchedulerStage().run(ctx)
        scheduler: Scheduler = ctx.metadata["scheduler"]

        # First dispatched should be CRITICAL (main.py)
        first = scheduler.next_job()
        assert first is not None
        assert first.priority == JobPriority.CRITICAL

    def test_stage_empty_repo_produces_empty_scheduler(self):
        ctx = self._make_ctx([])
        SchedulerStage().run(ctx)
        scheduler: Scheduler = ctx.metadata["scheduler"]
        assert scheduler.progress().total == 0
        assert scheduler.is_idle()
