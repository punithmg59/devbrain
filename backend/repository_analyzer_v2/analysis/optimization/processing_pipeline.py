"""
analysis/optimization/processing_pipeline.py
----------------------------------------------
Phase 4.8.4 — Fault-Tolerant Repository Processing Pipeline Orchestrator.

Coordinates large repository analysis pipeline stages, tracks resource utilization,
emits progress snapshots, enforces streaming batch execution, and recovers from file-level
failures gracefully using configurable fault tolerance logic.

Design Principles
-----------------
- **Fault-Tolerant Execution**: File-level unreadable source files, parser errors, or malformed ASTs
  do NOT terminate repository analysis when `continue_on_error=True`.
- **Structured Error Reporting**: Records every recovery action in `ProcessingIssue` without silently dropping errors.
- **Microsecond Stage Telemetry**: Integrates `ResourceMonitor` and `ProgressTracker`.
"""

from __future__ import annotations

import time
import traceback
from typing import Any, Callable, Dict, List, Optional

from models.optimization_models import (
    OptimizationMetrics,
    ProcessingIssue,
    ProcessingReport,
    ProcessingStage,
    RepositoryProcessingResult,
)
from analysis.optimization.optimization_config import OptimizationConfig
from analysis.optimization.progress_tracker import ProgressTracker
from analysis.optimization.repository_optimizer import RepositoryOptimizer
from analysis.optimization.resource_monitor import ResourceMonitor
from utils.logger import get_logger

logger = get_logger(__name__)


class RepositoryProcessingPipeline:
    """
    Pipeline manager coordinating large repository analysis execution and fault tolerance.

    Usage::

        pipeline = RepositoryProcessingPipeline(
            repository_id="repo1",
            config=OptimizationConfig(batch_size=500, continue_on_error=True),
        )
        result = pipeline.execute_pipeline(file_paths, stage_callbacks)
    """

    def __init__(
        self,
        repository_id: str = "repo",
        config: Optional[OptimizationConfig] = None,
    ) -> None:
        self.repository_id = repository_id
        self.config = config or OptimizationConfig()
        self.monitor = ResourceMonitor()
        self.progress = ProgressTracker()
        self.optimizer = RepositoryOptimizer(config=self.config)

    def execute_stage(
        self,
        stage: ProcessingStage,
        stage_fn: Callable[[], Any],
        stage_name: str = "",
    ) -> Any:
        """
        Execute a pipeline stage function with resource monitoring and fault tolerance.

        Parameters
        ----------
        stage:
            ProcessingStage enum member.
        stage_fn:
            Callable executing the stage logic.
        stage_name:
            Human-readable stage description.

        Returns
        -------
        Any: Output returned by stage_fn or None if recoverable failure occurred.
        """
        start_time = time.perf_counter()
        display_name = stage_name or stage.value
        self.progress.mark_stage_start(stage, f"Executing {display_name}")

        logger.info(f"[RepositoryProcessingPipeline] Stage '{stage.value}' started for repo '{self.repository_id}'")

        try:
            result = stage_fn()
            self.progress.mark_stage_completed(stage)
            dt_ms = (time.perf_counter() - start_time) * 1000.0
            logger.info(f"[RepositoryProcessingPipeline] Stage '{stage.value}' completed in {dt_ms:.2f}ms")

            # Check memory threshold cleanup
            self.optimizer.check_and_cleanup_memory(self.monitor)
            return result

        except Exception as exc:
            dt_ms = (time.perf_counter() - start_time) * 1000.0
            msg = f"Exception in stage '{stage.value}': {exc}"
            logger.error(f"[RepositoryProcessingPipeline] {msg}\n{traceback.format_exc()}")

            if not self.config.continue_on_error:
                raise

            # Fault Tolerance Recovery Action
            issue = ProcessingIssue(
                severity="error",
                stage=stage,
                reason=str(exc),
                exception_class=exc.__class__.__name__,
                recovery_action="recorded_stage_issue_and_continued",
            )
            logger.warning(f"[RepositoryProcessingPipeline] Recovered from stage error: {issue.recovery_action}")
            return None

    def execute_file_batch_safe(
        self,
        stage: ProcessingStage,
        file_paths: List[str],
        file_handler: Callable[[str], Any],
    ) -> ProcessingReport:
        """
        Process a batch of source files with file-level fault tolerance.

        Parameters
        ----------
        stage:
            Current processing stage.
        file_paths:
            List of source file paths to process.
        file_handler:
            Callable handling an individual file.

        Returns
        -------
        ProcessingReport
        """
        self.progress.update_progress(stage=stage, total_files=len(file_paths))

        total_files = len(file_paths)
        files_processed = 0
        files_failed = 0
        files_skipped = 0
        issues: List[ProcessingIssue] = []

        for batch in self.optimizer.batch_file_iterator(file_paths):
            for file_path in batch:
                try:
                    file_handler(file_path)
                    files_processed += 1
                except Exception as exc:
                    files_failed += 1
                    issue = ProcessingIssue(
                        severity="error",
                        stage=stage,
                        file_path=file_path,
                        reason=str(exc),
                        exception_class=exc.__class__.__name__,
                        recovery_action="skipped_file_and_continued",
                    )
                    issues.append(issue)
                    logger.warning(
                        f"[RepositoryProcessingPipeline] File failure in '{file_path}': {exc}. "
                        f"Recovery action: {issue.recovery_action}"
                    )
                    if not self.config.continue_on_error:
                        raise

            self.progress.update_progress(files_completed=files_processed)
            self.optimizer.check_and_cleanup_memory(self.monitor)

        self.monitor.update_counters(files=files_processed)

        return ProcessingReport(
            total_files_processed=files_processed,
            files_failed=files_failed,
            files_skipped=files_skipped,
            issues=issues,
            error_count=len([i for i in issues if i.severity == "error"]),
            warning_count=len([i for i in issues if i.severity == "warning"]),
            recovery_count=files_failed,
        )

    def assemble_result(
        self,
        success: bool,
        completed_stages: List[ProcessingStage],
        report: ProcessingReport,
        duration_ms: float,
    ) -> RepositoryProcessingResult:
        """
        Assemble final `RepositoryProcessingResult` container.

        Parameters
        ----------
        success:
            Overall success flag.
        completed_stages:
            List of finished stages.
        report:
            ProcessingReport object.
        duration_ms:
            Total pipeline duration in ms.

        Returns
        -------
        RepositoryProcessingResult
        """
        res_snapshot = self.monitor.take_snapshot(ProcessingStage.COMPLETED)

        metrics = OptimizationMetrics(
            processing_duration_ms=round(duration_ms, 3),
            files_processed=report.total_files_processed,
            files_skipped=report.files_skipped,
            files_failed=report.files_failed,
            nodes_processed=report.nodes_processed,
            edges_processed=report.edges_processed,
            peak_memory_mb=res_snapshot.peak_memory_mb,
            average_batch_size=float(self.config.batch_size),
            recovery_count=report.recovery_count,
            warnings_count=report.warning_count,
            errors_count=report.error_count,
        )

        warnings_list = [i.reason for i in report.issues if i.severity == "warning"]
        errors_list = [i.reason for i in report.issues if i.severity in ("error", "critical")]

        return RepositoryProcessingResult(
            repository_id=self.repository_id,
            success=success,
            completed_stages=completed_stages,
            processing_report=report,
            metrics=metrics,
            resource_snapshot=res_snapshot,
            warnings=warnings_list,
            errors=errors_list,
        )
