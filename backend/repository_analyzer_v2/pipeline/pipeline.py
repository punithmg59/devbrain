"""
pipeline/pipeline.py
--------------------
Orchestrates the ordered execution of all pipeline stages.
"""
from __future__ import annotations

import logging
import time
from typing import Callable, List, Optional

from pipeline.stage import (
    PipelineCompletedEvent,
    PipelineEvent,
    PipelineFailedEvent,
    Stage,
)
from pipeline.context import PipelineContext
from utils.exceptions import PipelineError, ErrorCode
from pipeline.discovery import DiscoveryStage
from pipeline.scheduler import SchedulerStage
from pipeline.parser import ParserStage
from pipeline.extractor import ExtractorStage
from pipeline.linker import LinkerStage
from pipeline.storage import StorageStage
from pipeline.validator import ValidatorStage
from pipeline.reporter import ReporterStage

logger = logging.getLogger(__name__)

# Default ordered stage sequence
DEFAULT_STAGES: List[Stage] = [
    DiscoveryStage(),
    SchedulerStage(),
    ParserStage(),
    ExtractorStage(),
    LinkerStage(),
    StorageStage(),
    ValidatorStage(),
    ReporterStage(),
]



class Pipeline:
    """
    Orchestrates an ordered sequence of Stage objects.

    Usage::

        ctx = PipelineContext(run_id="run-1", repository_id="repo-abc")
        pipeline = Pipeline()
        pipeline.run(ctx)
    """

    def __init__(
        self,
        stages: Optional[List[Stage]] = None,
        on_event: Optional[Callable[[PipelineEvent], None]] = None,
    ):
        """
        :param stages:   Ordered list of Stage objects; defaults to DEFAULT_STAGES.
        :param on_event: Optional event bus callback for lifecycle events.
        """
        self._stages: List[Stage] = stages if stages is not None else DEFAULT_STAGES
        self._on_event = on_event

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def run(self, ctx: PipelineContext) -> PipelineContext:
        """
        Execute stages in order.  Stops immediately if any stage raises.

        :returns: The mutated PipelineContext (metrics, metadata, errors filled in).
        :raises PipelineError: wrapping the original exception plus the stage name.
        """
        logger.info(
            f"[Pipeline] Starting run_id={ctx.run_id} "
            f"repo={ctx.repository_id} "
            f"stages={[s.name for s in self._stages]}"
        )
        ctx.start()
        wall_start = time.monotonic()
        stages_completed: List[str] = []

        for stage in self._stages:
            try:
                stage.run(ctx, event_bus=self._on_event)
                stages_completed.append(stage.name)
            except Exception as exc:
                total_ms = (time.monotonic() - wall_start) * 1000
                logger.error(
                    f"[Pipeline] Aborted at '{stage.name}' after {total_ms:.1f} ms "
                    f"(run_id={ctx.run_id})"
                )
                ctx.mark_failed()
                self._emit(PipelineFailedEvent(
                    failed_stage=stage.name,
                    error=exc,
                    total_duration_ms=total_ms,
                ))
                raise PipelineError(
                    f"Pipeline failed at stage '{stage.name}': {exc}",
                    code=ErrorCode.PIPELINE_STAGE_FAILED,
                    stage_name=stage.name,
                    cause=exc,
                ) from exc

        total_ms = (time.monotonic() - wall_start) * 1000
        ctx.mark_completed()
        logger.info(
            f"[Pipeline] Completed run_id={ctx.run_id} in {total_ms:.1f} ms"
        )
        self._emit(PipelineCompletedEvent(
            total_duration_ms=total_ms,
            stages_run=stages_completed,
        ))
        return ctx

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _emit(self, event: PipelineEvent) -> None:
        if self._on_event is not None:
            try:
                self._on_event(event)
            except Exception:
                pass  # event bus errors must never crash the pipeline
