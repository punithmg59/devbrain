"""
analysis/optimization/progress_tracker.py
-----------------------------------------
Phase 4.8.4 — Pipeline Progress Tracker.

Provides a report-only telemetry component for tracking stage progression, completed
stages, file counts, completion percentages, and estimated time remaining (ETA).

Design Principles
-----------------
- **Report-Only**: Strictly tracks and reports progress; NEVER alters or controls pipeline execution.
- **Microsecond Telemetry**: Fast non-blocking updates without disk or network I/O overhead.
"""

from __future__ import annotations

import time
from typing import List, Optional

from models.optimization_models import ProcessingStage, ProgressSnapshot
from utils.logger import get_logger

logger = get_logger(__name__)


class ProgressTracker:
    """
    Report-only progress telemetry tracker.

    Usage::

        tracker = ProgressTracker(total_files=1127)
        tracker.update_progress(ProcessingStage.PARSING, files_completed=500, current_op="Parsing app/main.py")
        snapshot = tracker.get_snapshot()
    """

    def __init__(self, total_files: int = 0, total_stages: int = 12) -> None:
        self.total_files = total_files
        self.total_stages = total_stages
        self._start_time = time.time()
        self._current_stage = ProcessingStage.DISCOVERY
        self._completed_stages: List[ProcessingStage] = []
        self._files_completed = 0
        self._current_operation = "Initializing"

    def mark_stage_start(self, stage: ProcessingStage, operation_msg: str = "") -> None:
        """Mark start of a new pipeline stage."""
        self._current_stage = stage
        self._current_operation = operation_msg or f"Starting stage {stage.value}"
        logger.debug(f"[ProgressTracker] Stage '{stage.value}' started: {self._current_operation}")

    def mark_stage_completed(self, stage: ProcessingStage) -> None:
        """Mark completion of a pipeline stage."""
        if stage not in self._completed_stages:
            self._completed_stages.append(stage)
        logger.debug(f"[ProgressTracker] Stage '{stage.value}' completed ({len(self._completed_stages)}/{self.total_stages})")

    def update_progress(
        self,
        stage: Optional[ProcessingStage] = None,
        files_completed: Optional[int] = None,
        total_files: Optional[int] = None,
        current_op: Optional[str] = None,
    ) -> None:
        """Update progress telemetry state."""
        if stage is not None:
            self._current_stage = stage
        if files_completed is not None:
            self._files_completed = files_completed
        if total_files is not None:
            self.total_files = total_files
        if current_op is not None:
            self._current_operation = current_op

    def get_snapshot(self) -> ProgressSnapshot:
        """
        Compute and return a ProgressSnapshot of current progress.

        Returns
        -------
        ProgressSnapshot
        """
        elapsed_sec = max(0.001, time.time() - self._start_time)

        # Stage ratio weight: 50% stage weight + 50% file weight
        stage_weight = (len(self._completed_stages) / float(max(1, self.total_stages))) * 50.0
        file_weight = 0.0
        if self.total_files > 0:
            file_weight = (min(self._files_completed, self.total_files) / float(self.total_files)) * 50.0

        pct_complete = round(min(100.0, stage_weight + file_weight), 1)

        # ETA estimation
        remaining_sec = 0.0
        if pct_complete > 1.0 and pct_complete < 100.0:
            total_est_sec = elapsed_sec / (pct_complete / 100.0)
            remaining_sec = round(max(0.0, total_est_sec - elapsed_sec), 1)

        return ProgressSnapshot(
            stage=self._current_stage,
            completed_stages=list(self._completed_stages),
            total_stages=self.total_stages,
            files_completed=self._files_completed,
            total_files=self.total_files,
            percentage_complete=pct_complete,
            estimated_remaining_sec=remaining_sec,
            current_operation=self._current_operation,
        )
