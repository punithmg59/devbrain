"""
tests/test_parser_metrics.py
----------------------------
Comprehensive unit and telemetry tests for Phase 3.8 — Parser Metrics & Telemetry System.
"""

from __future__ import annotations

import json
import pytest

from core.execution_context import ExecutionContext
from core.parser_manager import ParserManager
from core.worker_pool import Worker
from models.job import AnalysisJob
from models.parser import (
    ParserFileMetrics,
    ParserLanguage,
    ParserTelemetrySummary,
)
from models.repository import Repository, RepositoryFile
from pipeline.context import PipelineContext
from plugins.parser_plugin import DummyParserPlugin
from utils.metrics import MetricsCollector


@pytest.fixture(autouse=True)
def reset_singletons():
    """Reset MetricsCollector and ParserManager before each test."""
    MetricsCollector.get_instance().reset()
    ParserManager.reset()
    yield
    MetricsCollector.get_instance().reset()
    ParserManager.reset()


def make_job(path: str = "src/main.py", language: str = "python") -> AnalysisJob:
    file = RepositoryFile(
        path=path,
        name=path.rsplit("/", 1)[-1],
        extension="py",
        language=language,
        size_bytes=100,
        line_count=10,
    )
    return AnalysisJob.from_repository_file(repository_id="repo-metrics-test", file=file)


def make_context(job: AnalysisJob, run_id: str = "run-telemetry-1") -> ExecutionContext:
    worker = Worker(worker_id="w-telemetry-1")
    repo = Repository(id="repo-metrics-test", url="/tmp", name="metrics-repo")
    pipeline_ctx = PipelineContext(run_id=run_id, repository=repo)
    return ExecutionContext(job=job, worker=worker, pipeline_context=pipeline_ctx)


def test_parser_file_metrics_model():
    metric = ParserFileMetrics(
        file_path="src/app.py",
        language=ParserLanguage.PYTHON,
        plugin_name="dummy-parser-python",
        parser_version="1.0.0",
        duration_ms=12.5,
        ast_node_count=42,
        memory_rss_mb=55.4,
        warning_count=1,
        error_count=0,
    )
    assert metric.file_path == "src/app.py"
    assert metric.duration_ms == 12.5
    assert metric.ast_node_count == 42


def test_metrics_collector_record_and_summary():
    mc = MetricsCollector.get_instance()
    run_id = "run-test-100"

    m1 = ParserFileMetrics(
        file_path="src/a.py",
        language=ParserLanguage.PYTHON,
        plugin_name="dummy-parser-python",
        parser_version="1.0.0",
        duration_ms=10.0,
        ast_node_count=20,
        memory_rss_mb=50.0,
        warning_count=1,
        error_count=0,
    )
    m2 = ParserFileMetrics(
        file_path="src/b.ts",
        language=ParserLanguage.TYPESCRIPT,
        plugin_name="dummy-parser-typescript",
        parser_version="1.1.0",
        duration_ms=15.0,
        ast_node_count=30,
        memory_rss_mb=65.0,
        warning_count=0,
        error_count=1,
    )

    mc.record_parser_file_metrics(run_id, m1)
    mc.record_parser_file_metrics(run_id, m2)

    summary = mc.get_parser_telemetry_summary(run_id)
    assert isinstance(summary, ParserTelemetrySummary)
    assert summary.total_files_parsed == 2
    assert summary.total_duration_ms == 25.0
    assert summary.total_ast_nodes == 50
    assert summary.total_warnings == 1
    assert summary.total_errors == 1
    assert summary.peak_memory_rss_mb == 65.0

    assert "python" in summary.by_language
    assert summary.by_language["python"]["ast_nodes"] == 20

    assert "dummy-parser-typescript" in summary.by_plugin
    assert summary.by_plugin["dummy-parser-typescript"]["count"] == 1


def test_parser_telemetry_json_export():
    mc = MetricsCollector.get_instance()
    run_id = "run-export-test"

    metric = ParserFileMetrics(
        file_path="src/main.py",
        language=ParserLanguage.PYTHON,
        plugin_name="dummy-parser-python",
        parser_version="1.0.0",
        duration_ms=5.2,
        ast_node_count=10,
        memory_rss_mb=40.0,
    )
    mc.record_parser_file_metrics(run_id, metric)

    json_str = mc.export_parser_telemetry_json(run_id)
    data = json.loads(json_str)

    assert data["run_id"] == run_id
    assert data["total_files_parsed"] == 1
    assert data["total_ast_nodes"] == 10
    assert len(data["file_metrics"]) == 1


@pytest.mark.asyncio
async def test_parser_manager_auto_records_telemetry():
    pm = ParserManager.get_instance()
    mc = MetricsCollector.get_instance()

    plugin = DummyParserPlugin(target_language=ParserLanguage.PYTHON)
    pm.register_parser(plugin)

    job = make_job("src/index.py", "python")
    ctx = make_context(job, run_id="run-auto-metrics")

    res = await pm.execute_parser(job, ctx)
    assert res.status.value == "success"

    summary = mc.get_parser_telemetry_summary("run-auto-metrics")
    assert summary.total_files_parsed == 1
    assert summary.total_ast_nodes > 0
    assert summary.file_metrics[0].file_path == "src/index.py"
