"""
core/execution_context.py
-------------------------
Phase 2.4 — Worker Execution Context.

Provides a thread-safe, strongly-typed execution context passed to workers
and plugins during job processing.

Design Principles
-----------------
- **Immutable Identifiers**: `context_id`, `job_id`, `worker_id`, and `repository_id`
  are set once at construction and exposed as read-only properties.
- **Dependency Carrier**: Bundles all runtime references required by a worker:
  `job`, `repository_file`, `worker`, `pipeline_context`, `plugin`, `metrics`,
  `logger`, and `config`.
- **Thread-Safe Operational State**: Mutators for `progress`, `temp_data`, `errors`,
  `warnings`, and `cancellation_token` acquire a reentrant lock (`threading.RLock`)
  so concurrent sub-tasks can update state safely.
- **Cancellation & Timeout Control**: Incorporates a `CancellationToken` for
  signaling job cancellation across async/thread boundaries.
"""

from __future__ import annotations

import asyncio
import logging
import threading
import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Union

from config.settings import AnalyzerSettings, get_settings
from core.worker_pool import Worker
from models.analysis import PipelineStage
from models.job import AnalysisJob
from models.repository import RepositoryFile
from utils.logger import get_logger
from utils.metrics import MetricsCollector

if TYPE_CHECKING:
    from pipeline.context import PipelineContext


# ---------------------------------------------------------------------------
# Thread-safe & Async-compatible Cancellation Token
# ---------------------------------------------------------------------------

class CancellationToken:
    """
    Thread-safe and async-compatible token for signaling task cancellation.
    """

    def __init__(self) -> None:
        self._event: threading.Event = threading.Event()

    @property
    def is_cancelled(self) -> bool:
        """Return True if cancellation has been requested."""
        return self._event.is_set()

    def cancel(self) -> None:
        """Signal cancellation."""
        self._event.set()

    def check_cancelled(self) -> None:
        """
        Raise `asyncio.CancelledError` if cancellation has been requested.
        """
        if self._event.is_set():
            raise asyncio.CancelledError("Execution was cancelled via CancellationToken.")


# ---------------------------------------------------------------------------
# ExecutionContext Class
# ---------------------------------------------------------------------------

class ExecutionContext:
    """
    Type-safe execution context instance provided to workers during job processing.
    """

    def __init__(
        self,
        job: AnalysisJob,
        worker: Worker,
        pipeline_context: PipelineContext,
        plugin: Optional[Any] = None,
        metrics: Optional[MetricsCollector] = None,
        logger: Optional[logging.Logger] = None,
        config: Optional[AnalyzerSettings] = None,
        current_stage: Union[str, PipelineStage] = PipelineStage.PARSING,
        timeout_seconds: float = 30.0,
        memory_budget_mb: int = 1024,
        cancellation_token: Optional[CancellationToken] = None,
    ) -> None:
        # ── Immutable Identifiers ──────────────────────────────────────────
        self._context_id: str = f"ctx-{uuid.uuid4().hex[:8]}"
        self._created_at: datetime = datetime.now(timezone.utc)

        # ── Core Dependencies ──────────────────────────────────────────────
        self.job: AnalysisJob = job
        self.worker: Worker = worker
        self.pipeline_context: PipelineContext = pipeline_context
        self.plugin: Optional[Any] = plugin
        self.metrics: MetricsCollector = metrics or MetricsCollector.get_instance()
        self.logger: logging.Logger = logger or get_logger(__name__)
        self.config: AnalyzerSettings = config or get_settings()

        # ── Execution Controls & Limits ───────────────────────────────────
        self._current_stage: str = (
            current_stage.value if isinstance(current_stage, PipelineStage) else str(current_stage)
        )
        self.timeout_seconds: float = timeout_seconds
        self.memory_budget_mb: int = memory_budget_mb
        self.cancellation_token: CancellationToken = cancellation_token or CancellationToken()

        # ── Thread-Safe Operational State ─────────────────────────────────
        self._progress: float = 0.0
        self._temp_data: Dict[str, Any] = {}
        self._errors: List[str] = []
        self._warnings: List[str] = []
        self._lock: threading.RLock = threading.RLock()

    # ------------------------------------------------------------------
    # Immutable Properties
    # ------------------------------------------------------------------

    @property
    def context_id(self) -> str:
        """Unique identifier for this ExecutionContext instance."""
        return self._context_id

    @property
    def job_id(self) -> str:
        """Convenience accessor for job.job_id."""
        return self.job.job_id

    @property
    def worker_id(self) -> str:
        """Convenience accessor for worker.worker_id."""
        return self.worker.worker_id

    @property
    def repository_id(self) -> str:
        """Convenience accessor for job.repository_id."""
        return self.job.repository_id

    @property
    def repository_file(self) -> RepositoryFile:
        """Convenience accessor for job.file."""
        return self.job.file

    @property
    def created_at(self) -> datetime:
        """Timestamp when context was created."""
        return self._created_at

    # ------------------------------------------------------------------
    # Thread-Safe Operational Properties & Mutators
    # ------------------------------------------------------------------

    @property
    def current_stage(self) -> str:
        """Current pipeline stage name."""
        with self._lock:
            return self._current_stage

    def set_current_stage(self, stage: Union[str, PipelineStage]) -> None:
        """Set the current stage name."""
        stage_name = stage.value if isinstance(stage, PipelineStage) else str(stage)
        with self._lock:
            self._current_stage = stage_name

    @property
    def progress(self) -> float:
        """Completion progress percentage (0.0 to 100.0)."""
        with self._lock:
            return self._progress

    def set_progress(self, value: float) -> None:
        """Set completion progress percentage (clamped 0.0 to 100.0)."""
        clamped = max(0.0, min(100.0, float(value)))
        with self._lock:
            self._progress = clamped

    @property
    def is_cancelled(self) -> bool:
        """Return True if cancellation has been requested on this context."""
        return self.cancellation_token.is_cancelled

    def cancel(self) -> None:
        """Request job execution cancellation."""
        self.cancellation_token.cancel()

    def check_cancelled(self) -> None:
        """Raise `asyncio.CancelledError` if cancellation requested."""
        self.cancellation_token.check_cancelled()

    # ── Temporary Data Store ──────────────────────────────────────────

    @property
    def temp_data(self) -> Dict[str, Any]:
        """Return a copy snapshot of temporary key-value store."""
        with self._lock:
            return dict(self._temp_data)

    def set_temp_data(self, key: str, value: Any) -> None:
        """Store a temporary key-value pair."""
        with self._lock:
            self._temp_data[key] = value

    def get_temp_data(self, key: str, default: Any = None) -> Any:
        """Retrieve a temporary key value."""
        with self._lock:
            return self._temp_data.get(key, default)

    # ── Errors & Warnings Store ────────────────────────────────────────

    @property
    def errors(self) -> List[str]:
        """Return a snapshot list of recorded errors."""
        with self._lock:
            return list(self._errors)

    def add_error(self, message: str) -> None:
        """Record an error message."""
        with self._lock:
            self._errors.append(message)
            self.pipeline_context.add_error(
                stage_name=self._current_stage,
                message=message,
                file_path=self.repository_file.path,
            )

    @property
    def warnings(self) -> List[str]:
        """Return a snapshot list of recorded warnings."""
        with self._lock:
            return list(self._warnings)

    def add_warning(self, message: str) -> None:
        """Record a warning message."""
        with self._lock:
            self._warnings.append(message)
            self.pipeline_context.add_warning(
                stage_name=self._current_stage,
                message=message,
                file_path=self.repository_file.path,
            )

    def __repr__(self) -> str:
        return (
            f"ExecutionContext("
            f"context_id={self._context_id!r}, "
            f"job_id={self.job_id!r}, "
            f"worker_id={self.worker_id!r}, "
            f"stage={self._current_stage!r}, "
            f"progress={self.progress:.1f}%)"
        )
