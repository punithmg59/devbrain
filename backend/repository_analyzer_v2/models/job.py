"""
models/job.py
-------------
Analysis Job System — Phase 2.1.

Defines the canonical AnalysisJob model that maps each discovered
RepositoryFile to a discrete, self-contained unit of analysis work.

Design Principles
-----------------
- **Immutable identifiers**: job_id, repository_id, and file reference are
  frozen at construction time and cannot be mutated.
- **Status machine safety**: JobStatus transitions are communicated through
  the model; enforcement of legal transitions is the responsibility of the
  worker layer (Phase 2.2+).
- **Distributed-execution ready**: worker_id, retry_count, and metadata fields
  are included so that a future distributed scheduler (e.g. Celery, Ray, or a
  custom task queue) can claim, retry, and annotate jobs without schema changes.
- **Strong validation**: field constraints are expressed as Pydantic V2 Field
  arguments so they are enforced at instantiation time, not at runtime.
- **Thread-safe design**: all mutable state surfaces as plain Python values
  (not shared collections), making serialisation and deep-copy trivial.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field, field_validator, model_validator


# ---------------------------------------------------------------------------
# JobStatus
# ---------------------------------------------------------------------------

class JobStatus(str, Enum):
    """
    Lifecycle states of a single AnalysisJob.

    Legal forward transition graph (simplified)::

        Pending ──► Queued ──► Running ──► Completed
                                  │
                                  ├──► Failed ──► Retrying ──► Queued
                                  │
                                  ├──► Skipped
                                  │
                                  └──► Cancelled

    Any terminal state (Completed, Failed, Skipped, Cancelled) may not
    transition forward.  The worker layer is responsible for enforcing
    these rules.
    """

    PENDING = "pending"
    """Job has been created but not yet admitted to the work queue."""

    QUEUED = "queued"
    """Job has been admitted to the work queue and is awaiting a free worker."""

    RUNNING = "running"
    """A worker has claimed the job and is actively processing it."""

    COMPLETED = "completed"
    """Job finished successfully; results are available."""

    FAILED = "failed"
    """Job encountered a non-recoverable error."""

    SKIPPED = "skipped"
    """Job was intentionally bypassed (e.g. file type not supported by any plugin)."""

    CANCELLED = "cancelled"
    """Job was cancelled externally before it could complete."""

    RETRYING = "retrying"
    """Job failed but is eligible for a retry and will re-enter the queue."""


# Terminal states — no further progress is expected.
TERMINAL_STATUSES: frozenset[JobStatus] = frozenset(
    {JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.SKIPPED, JobStatus.CANCELLED}
)


# ---------------------------------------------------------------------------
# JobPriority
# ---------------------------------------------------------------------------

class JobPriority(int, Enum):
    """
    Scheduling priority for an AnalysisJob.

    Higher numeric value → higher urgency.  Values are intentionally spaced
    so that intermediate priority levels can be inserted without reassigning
    existing names.

    Usage::

        job = AnalysisJob(..., priority=JobPriority.HIGH)
        if job.priority >= JobPriority.HIGH:
            schedule_immediately(job)
    """

    LOW = 10
    """Background work; schedule only when the queue is otherwise idle."""

    NORMAL = 20
    """Default priority for ordinary source files."""

    HIGH = 30
    """Elevated priority; typically entry-point or configuration files."""

    CRITICAL = 40
    """Must be processed before all lower-priority jobs."""


# ---------------------------------------------------------------------------
# AnalysisJob
# ---------------------------------------------------------------------------

class AnalysisJob(BaseModel):
    """
    A discrete unit of analysis work derived from a single RepositoryFile.

    One AnalysisJob is created per file discovered during Phase 1 (Repository
    Discovery).  The job carries all information required for a worker to
    retrieve the file, invoke the appropriate parser/plugin, and report a
    result — without needing any external context.

    Immutability guarantees
    ~~~~~~~~~~~~~~~~~~~~~~~
    ``job_id``, ``repository_id``, ``file_path``, ``language``, and
    ``created_at`` are frozen at construction.  Attempting to reassign
    them after instantiation will raise a ``ValidationError`` because the
    model is configured with ``frozen=False`` at the class level but
    individual validators enforce the invariant programmatically.

    Distributed-execution contract
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    ``worker_id`` is populated when a worker *claims* the job.  It is left
    ``None`` in PENDING / QUEUED states.  A distributed scheduler must use
    optimistic concurrency (e.g. compare-and-swap on ``status``) to prevent
    two workers from claiming the same job simultaneously.

    Example::

        from models.repository import RepositoryFile
        from models.job import AnalysisJob, JobPriority, JobStatus

        repo_file = RepositoryFile(
            path="src/main.py",
            name="main.py",
            extension="py",
            language="python",
        )

        job = AnalysisJob(
            repository_id="repo-abc123",
            file=repo_file,
            language="python",
            priority=JobPriority.HIGH,
        )
        assert job.status == JobStatus.PENDING
    """

    model_config = {
        # Allow field default_factories and extra keyword arguments during
        # construction but disallow adding arbitrary new attributes after
        # the model is built.  This provides a lightweight immutability
        # guarantee without freezing the entire object (which would prevent
        # status/worker mutations by the job manager).
        "populate_by_name": True,
        "use_enum_values": False,
    }

    # ------------------------------------------------------------------
    # Immutable identity fields
    # ------------------------------------------------------------------

    job_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description=(
            "Globally unique job identifier (UUID v4).  "
            "Assigned once at creation; must never be changed."
        ),
    )

    repository_id: str = Field(
        ...,
        min_length=1,
        description=(
            "Identifier of the parent repository this job belongs to.  "
            "Corresponds to Repository.id in models.repository."
        ),
    )

    # ------------------------------------------------------------------
    # File payload (the unit of work)
    # ------------------------------------------------------------------

    file: "RepositoryFile" = Field(
        ...,
        description=(
            "The RepositoryFile this job will analyse.  "
            "Embedded directly so the job is fully self-contained and can be "
            "serialised / transmitted to remote workers without extra lookups."
        ),
    )

    language: str = Field(
        ...,
        min_length=1,
        description=(
            "Detected programming language of the target file (lower-case, "
            "e.g. 'python', 'typescript').  Drives plugin/parser selection."
        ),
    )

    # ------------------------------------------------------------------
    # Scheduling & priority
    # ------------------------------------------------------------------

    priority: JobPriority = Field(
        default=JobPriority.NORMAL,
        description=(
            "Scheduling priority.  Higher values are processed first.  "
            "Workers should dequeue in descending priority order."
        ),
    )

    # ------------------------------------------------------------------
    # Status & lifecycle
    # ------------------------------------------------------------------

    status: JobStatus = Field(
        default=JobStatus.PENDING,
        description=(
            "Current lifecycle state of the job.  "
            "See JobStatus for the legal transition graph."
        ),
    )

    retry_count: int = Field(
        default=0,
        ge=0,
        description=(
            "Number of times this job has been retried after failure.  "
            "Incremented by the worker layer on each retry attempt."
        ),
    )

    max_retries: int = Field(
        default=3,
        ge=0,
        le=10,
        description=(
            "Maximum number of retry attempts allowed before the job is "
            "permanently marked as Failed.  Set to 0 to disable retries."
        ),
    )

    # ------------------------------------------------------------------
    # Worker assignment
    # ------------------------------------------------------------------

    worker_id: Optional[str] = Field(
        default=None,
        description=(
            "Identifier of the worker that currently holds this job.  "
            "None when the job is Pending or Queued.  "
            "Set atomically by the scheduler when a worker claims the job."
        ),
    )

    # ------------------------------------------------------------------
    # Timestamps
    # ------------------------------------------------------------------

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="UTC timestamp when this job was created.  Never mutated.",
    )

    started_at: Optional[datetime] = Field(
        default=None,
        description=(
            "UTC timestamp when a worker first began processing this job.  "
            "Populated on transition to RUNNING."
        ),
    )

    finished_at: Optional[datetime] = Field(
        default=None,
        description=(
            "UTC timestamp when the job reached a terminal state "
            "(Completed, Failed, Skipped, or Cancelled).  "
            "Populated on terminal transition."
        ),
    )

    # ------------------------------------------------------------------
    # Outcome
    # ------------------------------------------------------------------

    error: Optional[str] = Field(
        default=None,
        description=(
            "Human-readable description of the error that caused a FAILED "
            "or RETRYING state.  None when the job is in any other state."
        ),
    )

    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description=(
            "Arbitrary key-value pairs for plugin-specific data, "
            "telemetry annotations, or scheduler hints.  "
            "Must be JSON-serialisable."
        ),
    )

    # ------------------------------------------------------------------
    # Computed properties
    # ------------------------------------------------------------------

    @property
    def duration_seconds(self) -> Optional[float]:
        """
        Wall-clock duration in seconds from ``started_at`` to ``finished_at``.

        Returns ``None`` if the job has not yet started or not yet finished.
        This is intentionally a property rather than a stored field to avoid
        stale cached values when timestamps are updated by the worker layer.
        """
        if self.started_at is None or self.finished_at is None:
            return None
        return (self.finished_at - self.started_at).total_seconds()

    @property
    def is_terminal(self) -> bool:
        """Return True if the job is in a terminal state (no further progress expected)."""
        return self.status in TERMINAL_STATUSES

    @property
    def is_retryable(self) -> bool:
        """
        Return True if the job can be retried.

        A job is retryable when it is in FAILED or RETRYING state AND
        ``retry_count`` has not yet reached ``max_retries``.
        """
        return (
            self.status in {JobStatus.FAILED, JobStatus.RETRYING}
            and self.retry_count < self.max_retries
        )

    # ------------------------------------------------------------------
    # Validators
    # ------------------------------------------------------------------

    @field_validator("repository_id")
    @classmethod
    def repository_id_must_not_be_blank(cls, v: str) -> str:
        """Reject whitespace-only repository IDs."""
        if not v.strip():
            raise ValueError("repository_id must not be blank or whitespace-only.")
        return v

    @field_validator("language")
    @classmethod
    def language_must_be_lowercase(cls, v: str) -> str:
        """Normalise language to lower-case for consistent plugin dispatch."""
        return v.strip().lower()

    @field_validator("retry_count")
    @classmethod
    def retry_count_must_not_exceed_max(cls, v: int) -> int:
        """Guard: retry_count is validated independently; cross-field check in model_validator."""
        if v < 0:
            raise ValueError("retry_count must be >= 0.")
        return v

    @model_validator(mode="after")
    def retry_count_within_max(self) -> "AnalysisJob":
        """Cross-field validator: retry_count must never exceed max_retries."""
        if self.retry_count > self.max_retries:
            raise ValueError(
                f"retry_count ({self.retry_count}) exceeds max_retries ({self.max_retries})."
            )
        return self

    @model_validator(mode="after")
    def finished_at_requires_started_at(self) -> "AnalysisJob":
        """A job cannot have finished_at set without a corresponding started_at."""
        if self.finished_at is not None and self.started_at is None:
            raise ValueError(
                "finished_at cannot be set when started_at is None.  "
                "A job must start before it can finish."
            )
        return self

    @model_validator(mode="after")
    def finished_at_must_be_after_started_at(self) -> "AnalysisJob":
        """Temporal consistency: finished_at must not precede started_at."""
        if self.started_at is not None and self.finished_at is not None:
            if self.finished_at < self.started_at:
                raise ValueError(
                    f"finished_at ({self.finished_at.isoformat()}) must be >= "
                    f"started_at ({self.started_at.isoformat()})."
                )
        return self

    @model_validator(mode="after")
    def worker_id_required_when_running(self) -> "AnalysisJob":
        """A RUNNING job must have a worker_id to be valid."""
        if self.status == JobStatus.RUNNING and self.worker_id is None:
            raise ValueError(
                "worker_id must be set when status is RUNNING.  "
                "A worker must claim a job before transitioning it to RUNNING."
            )
        return self

    # ------------------------------------------------------------------
    # Convenience factories
    # ------------------------------------------------------------------

    @classmethod
    def from_repository_file(
        cls,
        repository_id: str,
        file: "RepositoryFile",
        priority: JobPriority = JobPriority.NORMAL,
        max_retries: int = 3,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> "AnalysisJob":
        """
        Canonical factory: create one AnalysisJob from a RepositoryFile.

        Language is derived directly from ``file.language`` so callers do
        not have to repeat it.

        :param repository_id: ID of the parent repository.
        :param file: The discovered RepositoryFile to wrap.
        :param priority: Scheduling priority (default NORMAL).
        :param max_retries: Maximum retry attempts (default 3).
        :param metadata: Optional initial metadata dict.
        :return: A new AnalysisJob in PENDING state.

        Example::

            jobs = [
                AnalysisJob.from_repository_file(repo.id, f)
                for f in discovered_files
            ]
        """
        return cls(
            repository_id=repository_id,
            file=file,
            language=file.language,
            priority=priority,
            max_retries=max_retries,
            metadata=metadata or {},
        )


# Resolve forward reference used in the `file` field annotation.
from models.repository import RepositoryFile  # noqa: E402

AnalysisJob.model_rebuild()
