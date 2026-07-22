import json
import threading
import pytest

from utils import MetricsCollector


@pytest.fixture(autouse=True)
def reset_metrics():
    collector = MetricsCollector.get_instance()
    collector.reset()
    yield collector
    collector.reset()


def test_singleton_behavior(reset_metrics):
    """Test that MetricsCollector acts as a singleton."""
    c1 = MetricsCollector.get_instance()
    c2 = MetricsCollector.get_instance()
    assert c1 is c2


def test_record_pipeline_and_stage_durations(reset_metrics):
    """Test recording pipeline and stage execution durations."""
    run_id = "run-101"
    reset_metrics.record_pipeline_duration(run_id, 450.555)
    reset_metrics.record_stage_duration(run_id, "Discovery", 50.12)
    reset_metrics.record_stage_duration(run_id, "Parser", 200.45)

    snapshot = reset_metrics.get_metrics_snapshot(run_id)
    assert snapshot["run_id"] == run_id
    assert snapshot["pipeline_duration_ms"] == 450.56
    assert snapshot["stage_durations_ms"]["Discovery"] == 50.12
    assert snapshot["stage_durations_ms"]["Parser"] == 200.45


def test_file_count_and_error_count(reset_metrics):
    """Test file count tracking and error count increments."""
    run_id = "run-102"
    reset_metrics.record_file_count(run_id, total_files=100, processed_files=85)
    reset_metrics.increment_error_count(run_id, 2)
    reset_metrics.increment_error_count(run_id, 1)

    snapshot = reset_metrics.get_metrics_snapshot(run_id)
    assert snapshot["file_count"]["total"] == 100
    assert snapshot["file_count"]["processed"] == 85
    assert snapshot["error_count"] == 3


def test_worker_utilization(reset_metrics):
    """Test worker utilization calculation."""
    run_id = "run-103"
    reset_metrics.record_worker_utilization(run_id, active_workers=3, total_workers=4)

    snapshot = reset_metrics.get_metrics_snapshot(run_id)
    assert snapshot["worker_utilization"]["active"] == 3
    assert snapshot["worker_utilization"]["total"] == 4
    assert snapshot["worker_utilization"]["utilization_percent"] == 75.0


def test_resource_usage_sampling(reset_metrics):
    """Test memory and CPU resource usage measurement."""
    usage = reset_metrics.get_system_resource_usage()
    assert "memory_rss_mb" in usage
    assert "cpu_percent" in usage
    assert usage["memory_rss_mb"] >= 0.0
    assert usage["cpu_percent"] >= 0.0


def test_export_json(reset_metrics):
    """Test exporting metrics snapshot to a valid JSON string."""
    run_id = "run-104"
    reset_metrics.record_pipeline_duration(run_id, 120.0)
    reset_metrics.record_stage_duration(run_id, "Linker", 30.0)
    reset_metrics.increment_error_count(run_id, 1)

    json_str = reset_metrics.export_json(run_id)
    data = json.loads(json_str)

    assert data["run_id"] == run_id
    assert data["pipeline_duration_ms"] == 120.0
    assert data["stage_durations_ms"]["Linker"] == 30.0
    assert data["error_count"] == 1
    assert "resources" in data


def test_thread_safety(reset_metrics):
    """Test thread-safe metric updates under concurrent execution."""
    run_id = "run-concurrent"

    def worker(i: int):
        reset_metrics.record_stage_duration(run_id, f"Stage_{i}", i * 10.0)
        reset_metrics.increment_error_count(run_id, 1)

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(15)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    snapshot = reset_metrics.get_metrics_snapshot(run_id)
    assert len(snapshot["stage_durations_ms"]) == 15
    assert snapshot["error_count"] == 15
