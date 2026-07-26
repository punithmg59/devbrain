"""
Unit tests for Observability & Diagnostics Engine Subsystem (Step 4.10).
"""

import time
import unittest
from graph_storage.diagnostics import (
    AlertManager,
    AlertPolicy,
    DiagnosticBuilder,
    HealthMonitor,
    IntegrityInspector,
    MetricsCollector,
    ObservabilityManager,
    OperationTimeline,
    PerformanceProfiler,
    StorageDiagnostics,
    TracingManager,
)


class TestMetricsProfilerAndTracing(unittest.TestCase):
    """Test suite for MetricsCollector, PerformanceProfiler, and TracingManager."""

    def test_metrics_collector(self):
        collector = MetricsCollector()
        collector.record_read(5)
        collector.record_write(2)
        collector.record_cache_hit()
        collector.record_cache_miss()

        snap = collector.registry.snapshot()
        self.assertEqual(snap["counters"]["reads_total"], 5)
        self.assertEqual(snap["counters"]["writes_total"], 2)
        self.assertEqual(snap["counters"]["cache_hits_total"], 1)
        self.assertEqual(snap["counters"]["cache_misses_total"], 1)

    def test_performance_profiler_histogram(self):
        profiler = PerformanceProfiler()
        for lat in [10.0, 20.0, 30.0, 40.0, 50.0, 100.0]:
            profiler.record_latency("read_segment", lat)

        hist = profiler.calculate_histogram("read_segment")
        self.assertEqual(hist.min_ms, 10.0)
        self.assertEqual(hist.max_ms, 100.0)
        self.assertGreater(hist.p90, 0.0)
        self.assertGreater(hist.avg_ms, 0.0)

    def test_tracing_manager(self):
        tm = TracingManager()
        span = tm.start_trace("segment_load")
        time.sleep(0.01)
        completed = tm.end_trace(span.trace_id)

        self.assertIsNotNone(completed)
        self.assertGreater(completed.duration_ms, 0.0)
        self.assertEqual(completed.operation, "segment_load")


class TestHealthAlertsAndDiagnostics(unittest.TestCase):
    """Test suite for HealthMonitor, AlertManager, StorageDiagnostics, and Timeline."""

    def test_health_monitor(self):
        hm = HealthMonitor()
        self.assertEqual(hm.overall_status(), "HEALTHY")

        hm.set_component_health("cache", "DEGRADED")
        self.assertEqual(hm.overall_status(), "DEGRADED")

        report = hm.generate_report()
        self.assertEqual(report.overall_health, "DEGRADED")
        self.assertIn("One or more components are reporting DEGRADED status", report.warnings)

    def test_alert_manager(self):
        policy = AlertPolicy(latency_threshold_ms=50.0)
        am = AlertManager(policy)

        self.assertIsNone(am.evaluate_latency(30.0, "read_op"))
        alert = am.evaluate_latency(100.0, "read_op")
        self.assertIsNotNone(alert)
        self.assertEqual(alert.severity, "WARNING")

    def test_operation_timeline_and_builder(self):
        timeline = OperationTimeline()
        timeline.record_operation("write_segment", 15.5)
        recs = timeline.get_timeline()
        self.assertEqual(len(recs), 1)
        self.assertEqual(recs[0].operation, "write_segment")

        builder = (
            DiagnosticBuilder()
            .add_finding("All checksums match")
            .add_warning("High memory usage")
            .set_severity("WARNING")
        )
        report = builder.build_diagnostic_report()
        self.assertEqual(len(report.findings), 1)
        self.assertEqual(len(report.warnings), 1)
        self.assertEqual(report.severity, "WARNING")

    def test_observability_manager_facade(self):
        om = ObservabilityManager()
        om.record_operation("read_segment", 25.0)
        om.record_error("write_segment", "Disk full")

        stats = om.collect_statistics()
        self.assertIsNotNone(stats)


if __name__ == "__main__":
    unittest.main()
