"""
tests/test_parser_sdk.py
-------------------------
Comprehensive unit tests for Phase 3.4 — Parser SDK & `ParserPlugin`.
"""

from __future__ import annotations

import pytest

from core.execution_context import ExecutionContext
from core.worker_pool import Worker
from models.health import HealthStatus
from models.job import AnalysisJob
from models.parser import (
    ParserLanguage,
    ParserOptions,
    ParserResult,
    ParserStatus,
)
from models.repository import Repository, RepositoryFile
from pipeline.context import PipelineContext
from plugins.parser_plugin import DummyParserPlugin, ParserPlugin
from utils.exceptions import ParserError


# ---------------------------------------------------------------------------
# Test Helpers
# ---------------------------------------------------------------------------

def make_job(path: str = "src/main.py", language: str = "python") -> AnalysisJob:
    repo_file = RepositoryFile(
        path=path,
        name=path.rsplit("/", 1)[-1],
        extension="py",
        language=language,
        size_bytes=120,
        line_count=10,
        hash_sha256="abc123hash",
    )
    return AnalysisJob.from_repository_file(
        repository_id="repo-sdk-test",
        file=repo_file,
    )


def make_context(job: AnalysisJob) -> ExecutionContext:
    worker = Worker(worker_id="w-sdk-1")
    repo = Repository(id="repo-sdk-test", url="/tmp", name="sdk-test-repo")
    pipeline_ctx = PipelineContext(run_id="run-sdk-1", repository=repo)
    return ExecutionContext(job=job, worker=worker, pipeline_context=pipeline_ctx)


# ---------------------------------------------------------------------------
# Abstract Base Class Enforcement Tests
# ---------------------------------------------------------------------------

def test_abstract_parser_plugin_cannot_be_instantiated():
    with pytest.raises(TypeError):
        ParserPlugin()  # type: ignore[abstract]


# ---------------------------------------------------------------------------
# DummyParserPlugin Tests
# ---------------------------------------------------------------------------

def test_dummy_parser_plugin_metadata_and_defaults():
    plugin = DummyParserPlugin(target_language=ParserLanguage.PYTHON)
    assert plugin.language == ParserLanguage.PYTHON
    assert plugin.version.semver == "1.0.0-dummy"
    assert plugin.capabilities.supports_ast is True
    assert not plugin.is_initialized


def test_dummy_parser_plugin_lifecycle_and_parse():
    plugin = DummyParserPlugin(target_language=ParserLanguage.TYPESCRIPT)
    job = make_job("src/app.ts", "typescript")
    ctx = make_context(job)

    # Calling parse before initialize raises ParserError
    with pytest.raises(ParserError, match="must be initialized"):
        plugin.parse(job, ctx)

    # Initialize
    plugin.initialize()
    assert plugin.is_initialized

    # Parse
    result = plugin.parse(job, ctx, options=ParserOptions())
    assert isinstance(result, ParserResult)
    assert result.job_id == job.job_id
    assert result.file_path == "src/app.ts"
    assert result.language == ParserLanguage.TYPESCRIPT
    assert result.status == ParserStatus.SUCCESS
    assert result.ast_root is not None
    assert result.statistics.lines_parsed == 10

    # Shutdown
    plugin.shutdown()
    assert not plugin.is_initialized


def test_dummy_parser_plugin_validate():
    plugin = DummyParserPlugin()
    assert plugin.validate("def foo(): return 42") is True
    assert plugin.validate("def foo(): SYNTAX_ERROR") is False


def test_dummy_parser_plugin_health_check():
    plugin = DummyParserPlugin(target_language=ParserLanguage.GO)
    
    # Uninitialized health
    health_before = plugin.health()
    assert health_before.status == HealthStatus.UNHEALTHY
    assert health_before.details["initialized"] is False

    # Initialized health
    plugin.initialize()
    health_after = plugin.health()
    assert health_after.status == HealthStatus.HEALTHY
    assert health_after.details["initialized"] is True

    # Shutdown health
    plugin.shutdown()
    health_shutdown = plugin.health()
    assert health_shutdown.status == HealthStatus.UNHEALTHY
