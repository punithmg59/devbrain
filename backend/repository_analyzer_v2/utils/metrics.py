import json
import os
import sys
import threading
import time
from typing import Any, Dict, List, Optional

from models.parser import ParserFileMetrics, ParserLanguage, ParserTelemetrySummary

try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False


class MetricsCollector:
    """
    Internal, thread-safe metrics collector for tracking pipeline performance,
    stage durations, resource usage (memory/CPU), file counts, worker utilization,
    error counts, and parser telemetry (Phase 3.8).
    """
    _instance: Optional["MetricsCollector"] = None
    _singleton_lock: threading.Lock = threading.Lock()

    def __init__(self) -> None:
        self._state_lock: threading.Lock = threading.Lock()
        self.reset()

    @classmethod
    def get_instance(cls) -> "MetricsCollector":
        """Singleton accessor for MetricsCollector."""
        with cls._singleton_lock:
            if cls._instance is None:
                cls._instance = cls()
            return cls._instance

    def reset(self) -> None:
        """Reset all collected metrics."""
        with getattr(self, "_state_lock", threading.Lock()):
            self._pipeline_durations: Dict[str, float] = {}
            self._stage_durations: Dict[str, Dict[str, float]] = {}
            self._file_counts: Dict[str, Dict[str, int]] = {}
            self._error_counts: Dict[str, int] = {}
            self._worker_utilization: Dict[str, Dict[str, int]] = {}
            self._parser_file_metrics: Dict[str, List[ParserFileMetrics]] = {}

    def record_pipeline_duration(self, run_id: str, duration_ms: float) -> None:
        """Record total duration for a pipeline run."""
        with self._state_lock:
            self._pipeline_durations[run_id] = round(duration_ms, 2)

    def record_stage_duration(self, run_id: str, stage_name: str, duration_ms: float) -> None:
        """Record execution duration for a specific stage within a run."""
        with self._state_lock:
            if run_id not in self._stage_durations:
                self._stage_durations[run_id] = {}
            self._stage_durations[run_id][stage_name] = round(duration_ms, 2)

    def record_file_count(self, run_id: str, total_files: int, processed_files: int) -> None:
        """Record total and processed file counts."""
        with self._state_lock:
            self._file_counts[run_id] = {
                "total": max(0, total_files),
                "processed": max(0, processed_files),
            }

    def increment_error_count(self, run_id: str, amount: int = 1) -> None:
        """Increment error count for a run."""
        with self._state_lock:
            self._error_counts[run_id] = self._error_counts.get(run_id, 0) + amount

    def record_worker_utilization(self, run_id: str, active_workers: int, total_workers: int) -> None:
        """Record worker pool utilization metrics."""
        with self._state_lock:
            self._worker_utilization[run_id] = {
                "active": max(0, active_workers),
                "total": max(0, total_workers),
                "utilization_percent": round(
                    (active_workers / total_workers * 100.0) if total_workers > 0 else 0.0, 2
                ),
            }

    # ------------------------------------------------------------------
    # Phase 3.8 — Parser Telemetry Extensions
    # ------------------------------------------------------------------

    def record_parser_file_metrics(self, run_id: str, metric: ParserFileMetrics) -> None:
        """Record telemetry metrics for a single file parse operation."""
        with self._state_lock:
            if run_id not in self._parser_file_metrics:
                self._parser_file_metrics[run_id] = []
            self._parser_file_metrics[run_id].append(metric)

    def get_parser_telemetry_summary(self, run_id: str) -> ParserTelemetrySummary:
        """Generate aggregate `ParserTelemetrySummary` for a pipeline run."""
        with self._state_lock:
            metrics_list = list(self._parser_file_metrics.get(run_id, []))

        total_files = len(metrics_list)
        total_duration = sum(m.duration_ms for m in metrics_list)
        total_ast_nodes = sum(m.ast_node_count for m in metrics_list)
        total_warnings = sum(m.warning_count for m in metrics_list)
        total_errors = sum(m.error_count for m in metrics_list)
        peak_memory = max((m.memory_rss_mb for m in metrics_list), default=0.0)

        by_language: Dict[str, Dict[str, Any]] = {}
        by_plugin: Dict[str, Dict[str, Any]] = {}

        for m in metrics_list:
            lang_key = m.language.value if isinstance(m.language, ParserLanguage) else str(m.language)
            plugin_key = m.plugin_name

            # Aggregate by language
            if lang_key not in by_language:
                by_language[lang_key] = {"count": 0, "duration_ms": 0.0, "ast_nodes": 0, "errors": 0}
            by_language[lang_key]["count"] += 1
            by_language[lang_key]["duration_ms"] = round(by_language[lang_key]["duration_ms"] + m.duration_ms, 2)
            by_language[lang_key]["ast_nodes"] += m.ast_node_count
            by_language[lang_key]["errors"] += m.error_count

            # Aggregate by plugin
            if plugin_key not in by_plugin:
                by_plugin[plugin_key] = {"count": 0, "duration_ms": 0.0, "version": m.parser_version}
            by_plugin[plugin_key]["count"] += 1
            by_plugin[plugin_key]["duration_ms"] = round(by_plugin[plugin_key]["duration_ms"] + m.duration_ms, 2)

        return ParserTelemetrySummary(
            run_id=run_id,
            total_files_parsed=total_files,
            total_duration_ms=round(total_duration, 2),
            total_ast_nodes=total_ast_nodes,
            total_warnings=total_warnings,
            total_errors=total_errors,
            peak_memory_rss_mb=round(peak_memory, 2),
            by_language=by_language,
            by_plugin=by_plugin,
            file_metrics=metrics_list,
        )

    def export_parser_telemetry_json(self, run_id: str, indent: int = 2) -> str:
        """Export parser telemetry summary as JSON string."""
        summary = self.get_parser_telemetry_summary(run_id)
        return summary.to_json(indent=indent)

    def get_system_resource_usage(self) -> Dict[str, float]:
        """Collect memory and CPU metrics for the current process."""
        memory_mb = 0.0
        cpu_percent = 0.0

        if HAS_PSUTIL:
            try:
                proc = psutil.Process(os.getpid())
                memory_mb = proc.memory_info().rss / (1024 * 1024)
                cpu_percent = proc.cpu_percent(interval=None)
            except Exception:
                pass
        else:
            try:
                import resource
                rusage = resource.getrusage(resource.RUSAGE_SELF)
                memory_mb = rusage.ru_maxrss / 1024.0  # Convert KB to MB on Linux/macOS
            except (ImportError, AttributeError):
                memory_mb = 0.0

        return {
            "memory_rss_mb": round(memory_mb, 2),
            "cpu_percent": round(cpu_percent, 2),
        }

    def get_metrics_snapshot(self, run_id: Optional[str] = None) -> Dict[str, Any]:
        """Get a snapshot of collected metrics (for a specific run_id or all runs)."""
        with self._state_lock:
            resources = self.get_system_resource_usage()
            if run_id:
                return {
                    "run_id": run_id,
                    "pipeline_duration_ms": self._pipeline_durations.get(run_id, 0.0),
                    "stage_durations_ms": self._stage_durations.get(run_id, {}),
                    "file_count": self._file_counts.get(run_id, {"total": 0, "processed": 0}),
                    "error_count": self._error_counts.get(run_id, 0),
                    "worker_utilization": self._worker_utilization.get(
                        run_id, {"active": 0, "total": 0, "utilization_percent": 0.0}
                    ),
                    "resources": resources,
                }
            else:
                return {
                    "pipeline_durations_ms": self._pipeline_durations.copy(),
                    "stage_durations_ms": self._stage_durations.copy(),
                    "file_counts": self._file_counts.copy(),
                    "error_counts": self._error_counts.copy(),
                    "worker_utilization": self._worker_utilization.copy(),
                    "resources": resources,
                }

    def export_json(self, run_id: Optional[str] = None, indent: Optional[int] = 2) -> str:
        """Export metrics as a formatted JSON string."""
        snapshot = self.get_metrics_snapshot(run_id)
        return json.dumps(snapshot, indent=indent)
