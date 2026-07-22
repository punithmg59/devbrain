"""
tests/test_parser_stage.py
---------------------------
Phase 3.7 — Unit & Integration Tests for ParserStage with ParserManager.

Verifies the workflow:
    Worker → ExecutionContext → ParserManager → ParserPlugin → ParserResult
"""

from __future__ import annotations

import pytest

from core.parser_manager import ParserManager
from core.scheduler import Scheduler
from models.job import AnalysisJob
from models.parser import ParserLanguage, ParserResult, ParserStatus
from models.repository import Repository, RepositoryFile
from pipeline.context import PipelineContext
from pipeline.parser import ParserStage
from plugins.parser_plugin import DummyParserPlugin


@pytest.fixture(autouse=True)
def reset_singletons():
    """Reset ParserManager singleton before and after each test."""
    ParserManager.reset()
    yield
    ParserManager.reset()


def make_context(files: list[tuple[str, str]]) -> tuple[PipelineContext, Scheduler]:
    """Helper to construct a PipelineContext with a populated Scheduler."""
    repo = Repository(id="repo-stage-test", url="/tmp", name="stage-test")
    ctx = PipelineContext(run_id="run-stage-1", repository=repo)

    scheduler = Scheduler()
    for path, lang in files:
        file = RepositoryFile(
            path=path,
            name=path.rsplit("/", 1)[-1],
            extension=path.rsplit(".", 1)[-1],
            language=lang,
            size_bytes=150,
            line_count=15,
        )
        job = AnalysisJob.from_repository_file(repository_id=repo.id, file=file)
        scheduler.submit(job)

    ctx.metadata["scheduler"] = scheduler
    return ctx, scheduler


def test_parser_stage_name():
    stage = ParserStage()
    assert stage.name == "Parser"


def test_parser_stage_setup_seeds_plugins():
    ctx, scheduler = make_context([
        ("src/main.py", "python"),
        ("src/app.ts", "typescript"),
    ])

    stage = ParserStage()
    stage.setup(ctx)

    pm = ParserManager.get_instance()
    assert pm.select_parser(ParserLanguage.PYTHON) is not None
    assert pm.select_parser(ParserLanguage.TYPESCRIPT) is not None


def test_parser_stage_execute_happy_path():
    ctx, scheduler = make_context([
        ("src/main.py", "python"),
        ("src/app.ts", "typescript"),
    ])

    stage = ParserStage()
    stage.setup(ctx)
    stage.execute(ctx)
    stage.teardown(ctx)

    results: list[ParserResult] = ctx.metadata.get("parser_results", [])
    assert len(results) == 2
    assert all(r.status == ParserStatus.SUCCESS for r in results)

    stats = ctx.metadata.get("parser_stage_stats", {})
    assert stats["total_results"] == 2
    assert stats["success"] == 2
    assert stats["unsupported"] == 0
    assert stats["failed"] == 0


def test_parser_stage_execute_unsupported_language():
    ctx, scheduler = make_context([
        ("src/script.lua", "lua"),
    ])

    stage = ParserStage()
    stage.setup(ctx)
    stage.execute(ctx)
    stage.teardown(ctx)

    results: list[ParserResult] = ctx.metadata.get("parser_results", [])
    assert len(results) == 1
    assert results[0].status == ParserStatus.UNSUPPORTED_LANGUAGE

    stats = ctx.metadata.get("parser_stage_stats", {})
    assert stats["unsupported"] == 1


def test_parser_stage_empty_scheduler():
    repo = Repository(id="repo-empty", url="/tmp", name="empty")
    ctx = PipelineContext(run_id="run-empty", repository=repo)
    ctx.metadata["scheduler"] = Scheduler()

    stage = ParserStage()
    stage.setup(ctx)
    stage.execute(ctx)
    stage.teardown(ctx)

    assert ctx.metadata["parser_results"] == []
    assert ctx.metadata["parser_stage_stats"]["total_results"] == 0


def test_parser_stage_lifecycle_runner():
    """Verify that stage.run() executes setup, execute, and teardown cleanly."""
    ctx, scheduler = make_context([
        ("src/utils.py", "python"),
    ])

    stage = ParserStage()
    stage.run(ctx)

    assert "engine_summary" in ctx.metadata
    assert "parser_results" in ctx.metadata
    assert len(ctx.metadata["parser_results"]) == 1
