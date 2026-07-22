"""
pipeline/context.py
-------------------
Rich, type-safe PipelineContext that carries all shared state across every
pipeline stage for a single analysis run.

Design principles
-----------------
* **Immutable identity fields** – run_id, repository, and started_at are set
  once at construction and exposed as read-only properties.
* **Mutable operational fields** – current_stage, current_file, status,
  progress, metrics, errors, warnings are intentionally mutable; stages
  advance them via dedicated mutator methods so the call-sites stay clean.
* **No business logic** – this class is a pure data carrier; stages own the logic.
"""
from __future__ import annotations

import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from models.analysis import PipelineStage
from models.repository import Repository


# ---------------------------------------------------------------------------
# Status enum
# ---------------------------------------------------------------------------

class RunStatus(str, Enum):
    """Lifecycle status of a single analysis run."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


# ---------------------------------------------------------------------------
# Lightweight value objects
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class StageMetrics:
    """
    Immutable snapshot of per-stage timing captured at the end of each stage.

    :param stage_name:   Name of the pipeline stage.
    :param duration_ms:  Wall-clock time in milliseconds.
    :param files_processed: Number of files handled during this stage.
    """
    stage_name: str
    duration_ms: float
    files_processed: int = 0
    extra: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ContextError:
    """
    Immutable record of a pipeline error.

    :param stage_name: Stage where the error occurred.
    :param message:    Human-readable description.
    :param exc_type:   Optional exception class name.
    :param file_path:  Optional path of the file being processed.
    """
    stage_name: str
    message: str
    exc_type: Optional[str] = None
    file_path: Optional[str] = None


@dataclass(frozen=True)
class ContextWarning:
    """
    Immutable record of a non-fatal pipeline warning.

    :param stage_name: Stage where the warning was generated.
    :param message:    Human-readable description.
    :param file_path:  Optional path of the file being processed.
    """
    stage_name: str
    message: str
    file_path: Optional[str] = None


# ---------------------------------------------------------------------------
# Progress tracker
# ---------------------------------------------------------------------------

@dataclass
class Progress:
    """
    Tracks how many files have been processed vs. total discovered.

    :param total_files:     Total files scheduled for analysis (set by Scheduler).
    :param processed_files: Files completed so far (incremented by stages).
    """
    total_files: int = 0
    processed_files: int = 0

    @property
    def percentage(self) -> float:
        """Returns completion percentage (0.0 – 100.0)."""
        if self.total_files == 0:
            return 0.0
        return min(100.0, (self.processed_files / self.total_files) * 100)

    def increment(self, count: int = 1) -> None:
        """Safely increment the processed file count."""
        self.processed_files = min(self.total_files, self.processed_files + count)


# ---------------------------------------------------------------------------
# Main PipelineContext
# ---------------------------------------------------------------------------

class PipelineContext:
    """
    Central state carrier for a single repository analysis run.

    Identity fields (set at construction, never changed):
        - run_id
        - repository
        - started_at

    Operational fields (advanced by stages via mutator methods):
        - status
        - current_stage
        - current_file
        - progress
        - metrics         (list of StageMetrics snapshots)
        - errors          (list of ContextError)
        - warnings        (list of ContextWarning)
        - ended_at        (set once by mark_completed / mark_failed)
        - metadata        (open dict for stage-to-stage data transfer)

    Thread-safety
    -------------
    All mutator methods acquire a reentrant lock so that a multi-threaded
    stage (e.g. a parallel file parser) can safely report progress without
    corrupting shared state.
    """

    # ------------------------------------------------------------------
    # Construction
    # ------------------------------------------------------------------

    def __init__(
        self,
        run_id: str,
        repository: Repository,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        :param run_id:      Unique identifier for this analysis run.
        :param repository:  The Repository being analysed (immutable after creation).
        :param metadata:    Optional pre-seeded metadata dict.
        """
        # ── Immutable identity ──────────────────────────────────────────
        self._run_id: str = run_id
        self._repository: Repository = repository
        self._started_at: datetime = datetime.now(tz=timezone.utc)

        # ── Mutable operational state ───────────────────────────────────
        self._status: RunStatus = RunStatus.PENDING
        self._current_stage: Optional[PipelineStage] = None
        self._current_file: Optional[str] = None
        self._ended_at: Optional[datetime] = None

        self._progress: Progress = Progress()
        self._metrics: List[StageMetrics] = []
        self._errors: List[ContextError] = []
        self._warnings: List[ContextWarning] = []
        self.metadata: Dict[str, Any] = metadata or {}

        # Thread-safety lock
        self._lock: threading.RLock = threading.RLock()

    # ------------------------------------------------------------------
    # Immutable identity properties
    # ------------------------------------------------------------------

    @property
    def run_id(self) -> str:
        """Unique identifier for this analysis run (immutable)."""
        return self._run_id

    @property
    def repository(self) -> Repository:
        """The Repository being analysed (immutable)."""
        return self._repository

    @property
    def repository_id(self) -> str:
        """Convenience accessor for repository.id."""
        return self._repository.id

    @property
    def started_at(self) -> datetime:
        """UTC timestamp when this run was created (immutable)."""
        return self._started_at

    # ------------------------------------------------------------------
    # Mutable state – read-only via properties, written via mutators
    # ------------------------------------------------------------------

    @property
    def status(self) -> RunStatus:
        """Current lifecycle status of the run."""
        return self._status

    @property
    def current_stage(self) -> Optional[PipelineStage]:
        """The pipeline stage currently executing, or None."""
        return self._current_stage

    @property
    def current_file(self) -> Optional[str]:
        """Relative path of the file currently being processed, or None."""
        return self._current_file

    @property
    def ended_at(self) -> Optional[datetime]:
        """UTC timestamp when the run finished (set once), or None."""
        return self._ended_at

    @property
    def progress(self) -> Progress:
        """Live progress tracker (total vs processed files)."""
        return self._progress

    @property
    def metrics(self) -> List[StageMetrics]:
        """Ordered list of per-stage timing snapshots (appended, never modified)."""
        with self._lock:
            return list(self._metrics)

    @property
    def errors(self) -> List[ContextError]:
        """List of all ContextError records accumulated so far."""
        with self._lock:
            return list(self._errors)

    @property
    def warnings(self) -> List[ContextWarning]:
        """List of all ContextWarning records accumulated so far."""
        with self._lock:
            return list(self._warnings)

    # ------------------------------------------------------------------
    # Mutators – the only way to change mutable state
    # ------------------------------------------------------------------

    def start(self) -> None:
        """Transition status to RUNNING. Should be called before the first stage."""
        with self._lock:
            if self._status != RunStatus.PENDING:
                raise RuntimeError(
                    f"Cannot start a run that is already in '{self._status}' state."
                )
            self._status = RunStatus.RUNNING

    def advance_stage(self, stage: PipelineStage) -> None:
        """
        Move the context into the next pipeline stage.

        :param stage: The PipelineStage enum value about to execute.
        """
        with self._lock:
            self._current_stage = stage
            self._current_file = None  # clear file pointer on new stage

    def set_current_file(self, path: Optional[str]) -> None:
        """
        Record which file is currently being processed.

        :param path: Relative file path, or None to clear.
        """
        with self._lock:
            self._current_file = path

    def record_metrics(self, metrics: StageMetrics) -> None:
        """
        Append an immutable StageMetrics snapshot for the completed stage.

        :param metrics: A StageMetrics instance.
        """
        with self._lock:
            self._metrics.append(metrics)

    def add_error(
        self,
        stage_name: str,
        message: str,
        exc_type: Optional[str] = None,
        file_path: Optional[str] = None,
    ) -> None:
        """
        Record a pipeline error.

        :param stage_name: Name of the stage that raised the error.
        :param message:    Human-readable message.
        :param exc_type:   Optional: type(exc).__name__.
        :param file_path:  Optional: file being processed when error occurred.
        """
        with self._lock:
            self._errors.append(
                ContextError(
                    stage_name=stage_name,
                    message=message,
                    exc_type=exc_type,
                    file_path=file_path,
                )
            )

    def add_warning(
        self,
        stage_name: str,
        message: str,
        file_path: Optional[str] = None,
    ) -> None:
        """
        Record a non-fatal warning.

        :param stage_name: Name of the stage generating the warning.
        :param message:    Human-readable message.
        :param file_path:  Optional: file being processed.
        """
        with self._lock:
            self._warnings.append(
                ContextWarning(
                    stage_name=stage_name,
                    message=message,
                    file_path=file_path,
                )
            )

    def mark_completed(self) -> None:
        """
        Transition to COMPLETED and record the end timestamp.
        Idempotent if already completed.
        """
        with self._lock:
            if self._status in (RunStatus.COMPLETED, RunStatus.FAILED):
                return
            self._status = RunStatus.COMPLETED
            self._ended_at = datetime.now(tz=timezone.utc)
            self._current_file = None

    def mark_failed(self) -> None:
        """
        Transition to FAILED and record the end timestamp.
        Idempotent if already failed.
        """
        with self._lock:
            if self._status == RunStatus.FAILED:
                return
            self._status = RunStatus.FAILED
            self._ended_at = datetime.now(tz=timezone.utc)

    # ------------------------------------------------------------------
    # Computed helpers
    # ------------------------------------------------------------------

    @property
    def has_errors(self) -> bool:
        """True if any errors have been recorded."""
        with self._lock:
            return bool(self._errors)

    @property
    def has_warnings(self) -> bool:
        """True if any warnings have been recorded."""
        with self._lock:
            return bool(self._warnings)

    @property
    def elapsed_seconds(self) -> float:
        """
        Wall-clock elapsed time in seconds.
        Uses ended_at if the run is finished, otherwise the current time.
        """
        end = self._ended_at or datetime.now(tz=timezone.utc)
        return (end - self._started_at).total_seconds()

    @property
    def total_duration_ms(self) -> float:
        """Sum of all recorded per-stage durations in milliseconds."""
        with self._lock:
            return sum(m.duration_ms for m in self._metrics)

    def __repr__(self) -> str:
        return (
            f"PipelineContext("
            f"run_id={self._run_id!r}, "
            f"repository_id={self.repository_id!r}, "
            f"status={self._status.value!r}, "
            f"stage={self._current_stage!r}, "
            f"progress={self._progress.percentage:.1f}%)"
        )
