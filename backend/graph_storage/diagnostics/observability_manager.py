"""
ObservabilityManager facade orchestrating metrics, tracing, health, profiling, and diagnostics.
"""

from typing import Dict, List, Optional

from graph_storage.cache.cache_manager import CacheManager
from graph_storage.diagnostics.alert_manager import AlertEvent, AlertManager, AlertPolicy
from graph_storage.diagnostics.health_monitor import HealthMonitor, HealthReport
from graph_storage.diagnostics.metrics_collector import MetricRegistry, MetricsCollector
from graph_storage.diagnostics.operation_timeline import OperationTimeline, TimelineRecord
from graph_storage.diagnostics.performance_profiler import LatencyHistogram, PerformanceProfiler
from graph_storage.diagnostics.storage_diagnostics import DiagnosticReport, StorageDiagnostics, SystemStatistics
from graph_storage.diagnostics.tracing_manager import TraceContext, TracingManager
from graph_storage.manifest.snapshot_manager import SnapshotManager
from graph_storage.partitioning.partition_manager import PartitionManager
from graph_storage.segment.segment_repository import SegmentRepository
from graph_storage.transaction.transaction_manager import TransactionManager


class ObservabilityManager:
    """Subsystem facade providing complete visibility into Graph Storage operations."""

    def __init__(
        self,
        segment_repository: Optional[SegmentRepository] = None,
        snapshot_manager: Optional[SnapshotManager] = None,
        partition_manager: Optional[PartitionManager] = None,
        cache_manager: Optional[CacheManager] = None,
        transaction_manager: Optional[TransactionManager] = None,
        alert_policy: Optional[AlertPolicy] = None,
    ):
        self.metrics_collector = MetricsCollector()
        self.health_monitor = HealthMonitor()
        self.tracing_manager = TracingManager()
        self.profiler = PerformanceProfiler()
        self.timeline = OperationTimeline()
        self.alert_manager = AlertManager(alert_policy)
        self.diagnostics = StorageDiagnostics(
            segment_repository, snapshot_manager, partition_manager, cache_manager, transaction_manager
        )

    def record_operation(self, operation: str, duration_ms: float, status: str = "SUCCESS") -> None:
        """Record an operation in metrics, timeline, and profiler."""
        if "read" in operation.lower():
            self.metrics_collector.record_read()
        elif "write" in operation.lower():
            self.metrics_collector.record_write()

        self.profiler.record_latency(operation, duration_ms)
        self.timeline.record_operation(operation, duration_ms, status)
        self.alert_manager.evaluate_latency(duration_ms, operation)

    def record_latency(self, operation: str, duration_ms: float) -> None:
        """Record latency measurement."""
        self.profiler.record_latency(operation, duration_ms)
        self.alert_manager.evaluate_latency(duration_ms, operation)

    def record_error(self, operation: str, error_message: str) -> None:
        """Record an error event."""
        self.metrics_collector.registry.increment_counter("errors_total")
        self.alert_manager.raise_alert("ERROR", f"Error in {operation}: {error_message}", operation)

    def record_metric(self, name: str, value: float) -> None:
        """Record custom metric."""
        self.metrics_collector.registry.set_gauge(name, value)

    def generate_report(self) -> DiagnosticReport:
        """Generate comprehensive diagnostic report."""
        return self.diagnostics.generate_report()

    def check_health(self) -> HealthReport:
        """Check overall system health."""
        return self.health_monitor.generate_report()

    def collect_statistics(self) -> SystemStatistics:
        """Collect system statistics."""
        return self.diagnostics.collect_system_statistics()
