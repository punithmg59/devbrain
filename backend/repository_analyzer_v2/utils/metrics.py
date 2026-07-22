import json
import os
import sys
import threading
import time
from typing import Any, Dict, Optional

try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False


class MetricsCollector:
    """
    Internal, thread-safe metrics collector for tracking pipeline performance,
    stage durations, resource usage (memory/CPU), file counts, worker utilization,
    and error counts.
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
