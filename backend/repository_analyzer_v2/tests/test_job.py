"""
tests/test_job.py
-----------------
Unit tests for Phase 2.1 — Analysis Job System.

Covers:
- JobStatus and JobPriority enum values and ordering
- AnalysisJob construction defaults and factories
- Field-level validators (blank repository_id, language normalisation)
- Cross-field model validators (retry_count > max_retries,
  finished_at without started_at, temporal order, RUNNING without worker_id)
- Computed properties (duration_seconds, is_terminal, is_retryable)
- AnalysisJob.from_repository_file convenience factory
- Batch creation from a list of RepositoryFile objects
- Serialisation round-trip via model_dump / model_validate
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from pydantic import ValidationError

from models.job import TERMINAL_STATUSES, AnalysisJob, JobPriority, JobStatus
from models.repository import RepositoryFile


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_file(
    path: str = "src/main.py",
    language: str = "python",
    size_bytes: int = 1024,
) -> RepositoryFile:
    """Return a minimal RepositoryFile suitable for job construction."""
    return RepositoryFile(
        path=path,
        name=path.split("/")[-1],
        extension=path.rsplit(".", 1)[-1] if "." in path else "",
        language=language,
        size_bytes=size_bytes,
    )


def make_job(**overrides) -> AnalysisJob:
    """Return a minimal valid AnalysisJob with optional field overrides."""
    defaults = dict(
        repository_id="repo-abc123",
        file=make_file(),
        language="python",
    )
    defaults.update(overrides)
    return AnalysisJob(**defaults)


# ---------------------------------------------------------------------------
# JobStatus Enum
# ---------------------------------------------------------------------------

class TestJobStatus:
    def test_all_values_are_strings(self):
        for status in JobStatus:
            assert isinstance(status.value, str)

    def test_expected_members_exist(self):
        members = {s.value for s in JobStatus}
        assert members == {
            "pending", "queued", "running", "completed",
            "failed", "skipped", "cancelled", "retrying",
        }

    def test_terminal_statuses_are_correct(self):
        assert TERMINAL_STATUSES == {
            JobStatus.COMPLETED,
            JobStatus.FAILED,
            JobStatus.SKIPPED,
            JobStatus.CANCELLED,
        }

    def test_non_terminal_statuses_not_in_terminal_set(self):
        non_terminal = {JobStatus.PENDING, JobStatus.QUEUED, JobStatus.RUNNING, JobStatus.RETRYING}
        assert non_terminal.isdisjoint(TERMINAL_STATUSES)


# ---------------------------------------------------------------------------
# JobPriority Enum
# ---------------------------------------------------------------------------

class TestJobPriority:
    def test_all_values_are_ints(self):
        for priority in JobPriority:
            assert isinstance(priority.value, int)

    def test_priority_ordering(self):
        assert JobPriority.LOW < JobPriority.NORMAL < JobPriority.HIGH < JobPriority.CRITICAL

    def test_critical_is_highest(self):
        assert JobPriority.CRITICAL == max(JobPriority, key=lambda p: p.value)

    def test_low_is_lowest(self):
        assert JobPriority.LOW == min(JobPriority, key=lambda p: p.value)


# ---------------------------------------------------------------------------
# AnalysisJob — defaults and identity
# ---------------------------------------------------------------------------

class TestAnalysisJobDefaults:
    def test_default_status_is_pending(self):
        job = make_job()
        assert job.status == JobStatus.PENDING

    def test_default_priority_is_normal(self):
        job = make_job()
        assert job.priority == JobPriority.NORMAL

    def test_default_retry_count_zero(self):
        job = make_job()
        assert job.retry_count == 0

    def test_default_max_retries_three(self):
        job = make_job()
        assert job.max_retries == 3

    def test_job_id_is_uuid_string(self):
        import re
        job = make_job()
        assert re.match(r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$", job.job_id)

    def test_unique_job_ids_per_instance(self):
        job1 = make_job()
        job2 = make_job()
        assert job1.job_id != job2.job_id

    def test_created_at_is_utc_datetime(self):
        job = make_job()
        assert job.created_at.tzinfo is not None
        assert job.created_at.tzinfo == timezone.utc

    def test_worker_id_defaults_to_none(self):
        job = make_job()
        assert job.worker_id is None

    def test_error_defaults_to_none(self):
        job = make_job()
        assert job.error is None

    def test_metadata_defaults_to_empty_dict(self):
        job = make_job()
        assert job.metadata == {}


# ---------------------------------------------------------------------------
# Field validators
# ---------------------------------------------------------------------------

class TestFieldValidators:
    def test_blank_repository_id_raises(self):
        with pytest.raises(ValidationError, match="repository_id"):
            make_job(repository_id="")

    def test_whitespace_repository_id_raises(self):
        with pytest.raises(ValidationError, match="repository_id"):
            make_job(repository_id="   ")

    def test_language_normalised_to_lowercase(self):
        job = make_job(language="Python")
        assert job.language == "python"

    def test_language_strips_whitespace(self):
        job = make_job(language="  typescript  ")
        assert job.language == "typescript"

    def test_negative_retry_count_raises(self):
        with pytest.raises(ValidationError):
            make_job(retry_count=-1)

    def test_max_retries_above_ten_raises(self):
        with pytest.raises(ValidationError):
            make_job(max_retries=11)


# ---------------------------------------------------------------------------
# Model (cross-field) validators
# ---------------------------------------------------------------------------

class TestModelValidators:
    def test_retry_count_exceeding_max_retries_raises(self):
        with pytest.raises(ValidationError, match="retry_count"):
            make_job(retry_count=4, max_retries=3)

    def test_retry_count_equal_to_max_retries_is_valid(self):
        job = make_job(retry_count=3, max_retries=3)
        assert job.retry_count == 3

    def test_finished_at_without_started_at_raises(self):
        with pytest.raises(ValidationError, match="finished_at"):
            make_job(finished_at=datetime.now(timezone.utc))

    def test_finished_at_before_started_at_raises(self):
        now = datetime.now(timezone.utc)
        with pytest.raises(ValidationError, match="finished_at"):
            make_job(started_at=now, finished_at=now - timedelta(seconds=5))

    def test_finished_at_equal_to_started_at_is_valid(self):
        now = datetime.now(timezone.utc)
        job = make_job(started_at=now, finished_at=now, status=JobStatus.COMPLETED, worker_id="w-1")
        assert job.duration_seconds == 0.0

    def test_running_without_worker_id_raises(self):
        with pytest.raises(ValidationError, match="worker_id"):
            make_job(status=JobStatus.RUNNING)

    def test_running_with_worker_id_is_valid(self):
        job = make_job(status=JobStatus.RUNNING, worker_id="worker-007")
        assert job.status == JobStatus.RUNNING
        assert job.worker_id == "worker-007"


# ---------------------------------------------------------------------------
# Computed properties
# ---------------------------------------------------------------------------

class TestComputedProperties:
    def test_duration_none_when_not_started(self):
        job = make_job()
        assert job.duration_seconds is None

    def test_duration_none_when_started_but_not_finished(self):
        job = make_job(started_at=datetime.now(timezone.utc), status=JobStatus.RUNNING, worker_id="w-1")
        assert job.duration_seconds is None

    def test_duration_calculates_correctly(self):
        start = datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        end = start + timedelta(seconds=42.5)
        job = make_job(
            status=JobStatus.COMPLETED,
            worker_id="w-1",
            started_at=start,
            finished_at=end,
        )
        assert job.duration_seconds == pytest.approx(42.5)

    def test_is_terminal_for_completed(self):
        job = make_job(status=JobStatus.COMPLETED, worker_id="w-1")
        assert job.is_terminal is True

    def test_is_terminal_for_failed(self):
        job = make_job(status=JobStatus.FAILED)
        assert job.is_terminal is True

    def test_is_terminal_for_skipped(self):
        job = make_job(status=JobStatus.SKIPPED)
        assert job.is_terminal is True

    def test_is_terminal_for_cancelled(self):
        job = make_job(status=JobStatus.CANCELLED)
        assert job.is_terminal is True

    def test_is_not_terminal_for_running(self):
        job = make_job(status=JobStatus.RUNNING, worker_id="w-1")
        assert job.is_terminal is False

    def test_is_not_terminal_for_pending(self):
        job = make_job()
        assert job.is_terminal is False

    def test_is_retryable_failed_under_max(self):
        job = make_job(status=JobStatus.FAILED, retry_count=1, max_retries=3)
        assert job.is_retryable is True

    def test_is_not_retryable_failed_at_max(self):
        job = make_job(status=JobStatus.FAILED, retry_count=3, max_retries=3)
        assert job.is_retryable is False

    def test_is_retryable_in_retrying_state(self):
        job = make_job(status=JobStatus.RETRYING, retry_count=2, max_retries=3)
        assert job.is_retryable is True

    def test_is_not_retryable_for_completed(self):
        job = make_job(status=JobStatus.COMPLETED, worker_id="w-1")
        assert job.is_retryable is False


# ---------------------------------------------------------------------------
# from_repository_file factory
# ---------------------------------------------------------------------------

class TestFromRepositoryFileFactory:
    def test_factory_creates_pending_job(self):
        f = make_file("lib/utils.ts", language="typescript")
        job = AnalysisJob.from_repository_file("repo-xyz", f)
        assert job.status == JobStatus.PENDING
        assert job.repository_id == "repo-xyz"
        assert job.language == "typescript"

    def test_factory_derives_language_from_file(self):
        f = make_file("Main.java", language="java")
        job = AnalysisJob.from_repository_file("repo-1", f)
        assert job.language == "java"

    def test_factory_applies_priority(self):
        f = make_file()
        job = AnalysisJob.from_repository_file("repo-1", f, priority=JobPriority.CRITICAL)
        assert job.priority == JobPriority.CRITICAL

    def test_factory_applies_max_retries(self):
        f = make_file()
        job = AnalysisJob.from_repository_file("repo-1", f, max_retries=5)
        assert job.max_retries == 5

    def test_factory_applies_metadata(self):
        f = make_file()
        meta = {"source": "ci", "branch": "main"}
        job = AnalysisJob.from_repository_file("repo-1", f, metadata=meta)
        assert job.metadata == meta

    def test_factory_assigns_unique_job_ids(self):
        f = make_file()
        jobs = [AnalysisJob.from_repository_file("repo-1", f) for _ in range(50)]
        ids = {j.job_id for j in jobs}
        assert len(ids) == 50


# ---------------------------------------------------------------------------
# Batch creation
# ---------------------------------------------------------------------------

class TestBatchCreation:
    def test_batch_from_multiple_files(self):
        files = [
            make_file("src/a.py", "python"),
            make_file("src/b.ts", "typescript"),
            make_file("src/c.go", "go"),
        ]
        jobs = [AnalysisJob.from_repository_file("repo-batch", f) for f in files]
        assert len(jobs) == 3
        languages = {j.language for j in jobs}
        assert languages == {"python", "typescript", "go"}

    def test_batch_all_start_pending(self):
        files = [make_file(f"src/f{i}.py") for i in range(10)]
        jobs = [AnalysisJob.from_repository_file("repo-x", f) for f in files]
        assert all(j.status == JobStatus.PENDING for j in jobs)


# ---------------------------------------------------------------------------
# Serialisation round-trip
# ---------------------------------------------------------------------------

class TestSerialisation:
    def test_model_dump_is_json_serialisable(self):
        import json
        job = make_job()
        data = job.model_dump(mode="json")
        # Should not raise
        serialised = json.dumps(data)
        assert len(serialised) > 0

    def test_round_trip_via_model_dump_and_validate(self):
        job = make_job(
            repository_id="repo-rt",
            language="go",
            priority=JobPriority.HIGH,
            metadata={"key": "value"},
        )
        data = job.model_dump()
        restored = AnalysisJob.model_validate(data)
        assert restored.job_id == job.job_id
        assert restored.repository_id == job.repository_id
        assert restored.language == job.language
        assert restored.priority == job.priority
        assert restored.metadata == job.metadata

    def test_enum_values_preserved_in_dump(self):
        job = make_job(status=JobStatus.QUEUED, priority=JobPriority.HIGH)
        data = job.model_dump()
        assert data["status"] == JobStatus.QUEUED
        assert data["priority"] == JobPriority.HIGH

    def test_model_dump_json_mode_encodes_enum_values_as_strings(self):
        job = make_job(priority=JobPriority.CRITICAL)
        data = job.model_dump(mode="json")
        # In JSON mode enums should serialise to their native Python values
        assert data["priority"] == JobPriority.CRITICAL.value or data["priority"] == 40
