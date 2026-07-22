"""
pipeline/stage.py
-----------------
Defines the abstract Stage interface and all pipeline lifecycle events.
PipelineContext is imported from pipeline.context.
"""
from __future__ import annotations

import logging
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

# Rich context lives in its own module (Phase 0.7)
from pipeline.context import PipelineContext, RunStatus, StageMetrics

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Events
# ---------------------------------------------------------------------------

class PipelineEvent:
    """Base class for pipeline lifecycle events."""
    pass


@dataclass
class StageStartedEvent(PipelineEvent):
    stage_name: str
    timestamp: float = field(default_factory=time.monotonic)


@dataclass
class StageCompletedEvent(PipelineEvent):
    stage_name: str
    duration_ms: float
    timestamp: float = field(default_factory=time.monotonic)


@dataclass
class StageFailedEvent(PipelineEvent):
    stage_name: str
    error: Exception
    duration_ms: float
    timestamp: float = field(default_factory=time.monotonic)


@dataclass
class PipelineCompletedEvent(PipelineEvent):
    total_duration_ms: float
    stages_run: List[str]


@dataclass
class PipelineFailedEvent(PipelineEvent):
    failed_stage: str
    error: Exception
    total_duration_ms: float


# ---------------------------------------------------------------------------
# Stage Abstract Base
# ---------------------------------------------------------------------------

class Stage(ABC):
    """
    Abstract base class for every pipeline stage.

    Lifecycle:
      1. setup(ctx)   – one-time initialization per run
      2. execute(ctx) – core work
      3. teardown(ctx)– cleanup regardless of success/failure
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable name of this stage."""

    @abstractmethod
    def setup(self, ctx: PipelineContext) -> None:
        """Called once before execute(). Use for resource acquisition."""

    @abstractmethod
    def execute(self, ctx: PipelineContext) -> None:
        """
        Main work for this stage.
        Raise an exception to signal failure and abort the pipeline.
        """

    @abstractmethod
    def teardown(self, ctx: PipelineContext) -> None:
        """Called after execute() (success *or* failure). Release resources here."""

    # ------------------------------------------------------------------
    # Internal runner – wraps the lifecycle with timing + event emission
    # ------------------------------------------------------------------

    def run(
        self,
        ctx: PipelineContext,
        event_bus: Optional[Callable[[PipelineEvent], None]] = None,
    ) -> None:
        """
        Runs the full stage lifecycle and records timing into ctx.timings.
        Emits StageStartedEvent, StageCompletedEvent or StageFailedEvent.
        """
        stage_logger = logging.getLogger(f"pipeline.{self.name}")
        stage_logger.info(f"[{self.name}] Starting stage")

        _emit(event_bus, StageStartedEvent(stage_name=self.name))
        start = time.monotonic()

        self.setup(ctx)
        try:
            self.execute(ctx)
            duration_ms = (time.monotonic() - start) * 1000
            # Record rich metrics on the context
            ctx.record_metrics(StageMetrics(stage_name=self.name, duration_ms=duration_ms))
            # Also keep the legacy timings dict for backward compat with pipeline.py
            ctx.metadata.setdefault("_timings", {})[self.name] = duration_ms
            stage_logger.info(f"[{self.name}] Completed in {duration_ms:.1f} ms")
            _emit(event_bus, StageCompletedEvent(stage_name=self.name, duration_ms=duration_ms))
        except Exception as exc:
            duration_ms = (time.monotonic() - start) * 1000
            ctx.add_error(
                stage_name=self.name,
                message=str(exc),
                exc_type=type(exc).__name__,
                file_path=ctx.current_file,
            )
            stage_logger.error(f"[{self.name}] Failed after {duration_ms:.1f} ms – {exc}")
            _emit(event_bus, StageFailedEvent(stage_name=self.name, error=exc, duration_ms=duration_ms))
            raise
        finally:
            self.teardown(ctx)


def _emit(bus: Optional[Callable[[PipelineEvent], None]], event: PipelineEvent) -> None:
    if bus is not None:
        try:
            bus(event)
        except Exception:
            pass  # event bus errors must never crash the pipeline
