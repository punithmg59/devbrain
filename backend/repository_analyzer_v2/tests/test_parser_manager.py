"""
tests/test_parser_manager.py
-----------------------------
Comprehensive unit and async tests for Phase 3.5 — Parser Manager & Plugin Registry.
"""

from __future__ import annotations

import pytest

from core.execution_context import ExecutionContext
from core.parser_manager import ParserManager
from core.worker_pool import Worker
from models.health import HealthStatus
from models.job import AnalysisJob
from models.parser import (
    ParserLanguage,
    ParserResult,
    ParserStatus,
)
from models.repository import Repository, RepositoryFile
from pipeline.context import PipelineContext
from plugins.parser_plugin import DummyParserPlugin, ParserPlugin
from utils.exceptions import PluginError


# ---------------------------------------------------------------------------
# Test Helpers & Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def reset_parser_manager():
    """Automatically reset ParserManager singleton before every test."""
    ParserManager.reset()
    yield
    ParserManager.reset()


def make_job(path: str = "src/main.py", language: str = "python") -> AnalysisJob:
    repo_file = RepositoryFile(
        path=path,
        name=path.rsplit("/", 1)[-1],
        extension=path.rsplit(".", 1)[-1],
        language=language,
        size_bytes=100,
        line_count=10,
    )
    return AnalysisJob.from_repository_file(
        repository_id="repo-mgr-test",
        file=repo_file,
    )


def make_context(job: AnalysisJob) -> ExecutionContext:
    worker = Worker(worker_id="w-mgr-1")
    repo = Repository(id="repo-mgr-test", url="/tmp", name="mgr-test-repo")
    pipeline_ctx = PipelineContext(run_id="run-mgr-1", repository=repo)
    return ExecutionContext(job=job, worker=worker, pipeline_context=pipeline_ctx)


# ---------------------------------------------------------------------------
# Singleton & Reset Tests
# ---------------------------------------------------------------------------

def test_parser_manager_singleton_behavior():
    pm1 = ParserManager.get_instance()
    pm2 = ParserManager.get_instance()
    assert pm1 is pm2

    ParserManager.reset()
    pm3 = ParserManager.get_instance()
    assert pm3 is not pm1


# ---------------------------------------------------------------------------
# Validation & Registration Tests
# ---------------------------------------------------------------------------

def test_register_and_select_parser():
    mgr = ParserManager.get_instance()
    python_plugin = DummyParserPlugin(target_language=ParserLanguage.PYTHON)
    ts_plugin = DummyParserPlugin(target_language=ParserLanguage.TYPESCRIPT)

    mgr.register_parser(python_plugin)
    mgr.register_parser(ts_plugin)

    assert len(mgr.get_registered_languages()) == 2

    selected_py = mgr.select_parser(ParserLanguage.PYTHON)
    assert selected_py is python_plugin

    selected_ts = mgr.select_parser("typescript")
    assert selected_ts is ts_plugin


def test_register_duplicate_language_raises():
    mgr = ParserManager.get_instance()
    p1 = DummyParserPlugin(target_language=ParserLanguage.PYTHON)
    p2 = DummyParserPlugin(target_language=ParserLanguage.PYTHON)

    mgr.register_parser(p1)
    with pytest.raises(PluginError, match="already registered"):
        mgr.register_parser(p2)


def test_validate_invalid_object_raises():
    mgr = ParserManager.get_instance()
    with pytest.raises(PluginError):
        mgr.validate_parser("not_a_plugin")  # type: ignore[arg-type]


def test_select_parser_by_file_extension():
    mgr = ParserManager.get_instance()
    python_plugin = DummyParserPlugin(target_language=ParserLanguage.PYTHON)
    mgr.register_parser(python_plugin)

    p_py = mgr.select_parser_by_file("src/main.py")
    assert p_py is python_plugin

    p_pyi = mgr.select_parser_by_file("stubs/types.pyi")
    assert p_pyi is python_plugin

    p_unknown = mgr.select_parser_by_file("config.yaml")
    assert p_unknown is None


def test_unregister_parser():
    mgr = ParserManager.get_instance()
    plugin = DummyParserPlugin(target_language=ParserLanguage.GO)
    mgr.register_parser(plugin)
    plugin.initialize()

    assert mgr.select_parser(ParserLanguage.GO) is plugin

    unregistered = mgr.unregister_parser(ParserLanguage.GO)
    assert unregistered is plugin
    assert not plugin.is_initialized
    assert mgr.select_parser(ParserLanguage.GO) is None


# ---------------------------------------------------------------------------
# Async Parser Execution Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_execute_parser_happy_path():
    mgr = ParserManager.get_instance()
    plugin = DummyParserPlugin(target_language=ParserLanguage.PYTHON)
    mgr.register_parser(plugin)

    job = make_job("src/app.py", "python")
    ctx = make_context(job)

    result = await mgr.execute_parser(job, ctx)

    assert isinstance(result, ParserResult)
    assert result.status == ParserStatus.SUCCESS
    assert result.language == ParserLanguage.PYTHON
    assert plugin.is_initialized


@pytest.mark.asyncio
async def test_execute_parser_unsupported_language():
    mgr = ParserManager.get_instance()
    job = make_job("src/script.lua", "lua")
    ctx = make_context(job)

    result = await mgr.execute_parser(job, ctx)

    assert isinstance(result, ParserResult)
    assert result.status == ParserStatus.UNSUPPORTED_LANGUAGE
    assert result.language == ParserLanguage.UNKNOWN


@pytest.mark.asyncio
async def test_execute_parser_error_isolation():
    mgr = ParserManager.get_instance()

    class CrashingParserPlugin(DummyParserPlugin):
        def parse(self, job, context, options=None):
            raise RuntimeError("Parser internal engine crash!")

    crashing_plugin = CrashingParserPlugin(target_language=ParserLanguage.CSHARP)
    mgr.register_parser(crashing_plugin)
    crashing_plugin.initialize()

    job = make_job("src/Program.cs", "csharp")
    ctx = make_context(job)

    result = await mgr.execute_parser(job, ctx)

    assert isinstance(result, ParserResult)
    assert result.status == ParserStatus.INTERNAL_ERROR
    assert len(result.errors) == 1
    assert "Parser execution crash" in result.errors[0].message


# ---------------------------------------------------------------------------
# Lifecycle Operations & Health Tests
# ---------------------------------------------------------------------------

def test_initialize_all_and_shutdown_all():
    mgr = ParserManager.get_instance()
    p1 = DummyParserPlugin(target_language=ParserLanguage.PYTHON)
    p2 = DummyParserPlugin(target_language=ParserLanguage.TYPESCRIPT)
    mgr.register_parser(p1)
    mgr.register_parser(p2)

    assert not p1.is_initialized
    assert not p2.is_initialized

    mgr.initialize_all()
    assert p1.is_initialized
    assert p2.is_initialized

    mgr.shutdown_all()
    assert not p1.is_initialized
    assert not p2.is_initialized


def test_health_check_aggregation():
    mgr = ParserManager.get_instance()
    p1 = DummyParserPlugin(target_language=ParserLanguage.PYTHON)
    mgr.register_parser(p1)

    health_before = mgr.health_check()
    assert health_before["python"].status == HealthStatus.UNHEALTHY

    mgr.initialize_all()
    health_after = mgr.health_check()
    assert health_after["python"].status == HealthStatus.HEALTHY
