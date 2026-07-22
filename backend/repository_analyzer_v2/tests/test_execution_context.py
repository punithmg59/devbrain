"""
tests/test_execution_context.py
--------------------------------
Comprehensive unit tests for Phase 2.4 — Execution Context.
"""

from __future__ import annotations

import asyncio
import threading
from typing import List

import pytest

from core.execution_context import CancellationToken, ExecutionContext
from core.worker_pool import Worker
from models.analysis import PipelineStage
from models.job import AnalysisJob
from models.repository import Repository, RepositoryFile
from pipeline.context import PipelineContext


# ---------------------------------------------------------------------------
# Test Helpers
# ---------------------------------------------------------------------------

def make_repository() -> Repository:
    return Repository(id="repo-exec-test", url="/tmp", name="exec-test-repo")


def make_file(path: str = "src/main.py", language: str = "python") -> RepositoryFile:
    return RepositoryFile(
        path=path,
        name=path.rsplit("/", 1)[-1],
        extension=path.rsplit(".", 1)[-1],
        language=language,
    )


def make_job(path: str = "src/main.py") -> AnalysisJob:
    return AnalysisJob.from_repository_file(
        repository_id="repo-exec-test",
        file=make_file(path),
    )


def make_context() -> ExecutionContext:
    job = make_job()
    worker = Worker(worker_id="w-exec-1")
    pipeline_ctx = PipelineContext(run_id="run-exec-1", repository=make_repository())
    return ExecutionContext(
        job=job,
        worker=worker,
        pipeline_context=pipeline_ctx,
        timeout_seconds=20.0,
        memory_budget_mb=512,
    )


# ---------------------------------------------------------------------------
# CancellationToken Tests
# ---------------------------------------------------------------------------

def test_cancellation_token_defaults():
    token = CancellationToken()
    assert not token.is_cancelled


def test_cancellation_token_cancel():
    token = CancellationToken()
    token.cancel()
    assert token.is_cancelled


def test_cancellation_token_check_cancelled():
    token = CancellationToken()
    # Should not raise when not cancelled
    token.check_cancelled()

    token.cancel()
    with pytest.raises(asyncio.CancelledError):
        token.check_cancelled()


# ---------------------------------------------------------------------------
# ExecutionContext Construction & Immutable Identifiers Tests
# ---------------------------------------------------------------------------

def test_execution_context_identifiers():
    ctx = make_context()
    assert ctx.context_id.startswith("ctx-")
    assert ctx.job_id == ctx.job.job_id
    assert ctx.worker_id == "w-exec-1"
    assert ctx.repository_id == "repo-exec-test"
    assert ctx.repository_file.path == "src/main.py"
    assert ctx.created_at is not None


def test_execution_context_dependencies():
    ctx = make_context()
    assert ctx.job is not None
    assert ctx.worker is not None
    assert ctx.pipeline_context is not None
    assert ctx.metrics is not None
    assert ctx.logger is not None
    assert ctx.config is not None


# ---------------------------------------------------------------------------
# Stage, Timeout, Memory Budget Controls Tests
# ---------------------------------------------------------------------------

def test_execution_context_stage_controls():
    ctx = make_context()
    assert ctx.current_stage == "parsing"

    ctx.set_current_stage(PipelineStage.EXTRACTION)
    assert ctx.current_stage == "extraction"

    ctx.set_current_stage("linking")
    assert ctx.current_stage == "linking"


def test_execution_context_timeout_and_memory_limits():
    ctx = make_context()
    assert ctx.timeout_seconds == 20.0
    assert ctx.memory_budget_mb == 512


# ---------------------------------------------------------------------------
# Progress Mutator Tests
# ---------------------------------------------------------------------------

def test_execution_context_progress_clamping():
    ctx = make_context()
    assert ctx.progress == 0.0

    ctx.set_progress(45.5)
    assert ctx.progress == 45.5

    # Clamp upper bound
    ctx.set_progress(150.0)
    assert ctx.progress == 100.0

    # Clamp lower bound
    ctx.set_progress(-20.0)
    assert ctx.progress == 0.0


# ---------------------------------------------------------------------------
# Temporary Data Store Tests
# ---------------------------------------------------------------------------

def test_execution_context_temp_data():
    ctx = make_context()
    assert ctx.temp_data == {}

    ctx.set_temp_data("ast_nodes_count", 42)
    assert ctx.get_temp_data("ast_nodes_count") == 42
    assert ctx.get_temp_data("missing_key", "default") == "default"

    snapshot = ctx.temp_data
    assert snapshot == {"ast_nodes_count": 42}

    # Snapshot modification must not mutate internal dict
    snapshot["ast_nodes_count"] = 999
    assert ctx.get_temp_data("ast_nodes_count") == 42


# ---------------------------------------------------------------------------
# Errors & Warnings Store Tests
# ---------------------------------------------------------------------------

def test_execution_context_errors_and_warnings():
    ctx = make_context()
    assert ctx.errors == []
    assert ctx.warnings == []

    ctx.add_error("Syntax error on line 12")
    ctx.add_warning("Unused import on line 3")

    assert ctx.errors == ["Syntax error on line 12"]
    assert ctx.warnings == ["Unused import on line 3"]

    # Verify propagation to PipelineContext
    assert ctx.pipeline_context.has_errors
    assert ctx.pipeline_context.has_warnings
    assert ctx.pipeline_context.errors[0].message == "Syntax error on line 12"
    assert ctx.pipeline_context.warnings[0].message == "Unused import on line 3"


# ---------------------------------------------------------------------------
# Cancellation Integration Tests
# ---------------------------------------------------------------------------

def test_execution_context_cancellation():
    ctx = make_context()
    assert not ctx.is_cancelled

    ctx.cancel()
    assert ctx.is_cancelled

    with pytest.raises(asyncio.CancelledError):
        ctx.check_cancelled()


# ---------------------------------------------------------------------------
# Thread Safety Tests
# ---------------------------------------------------------------------------

def test_execution_context_thread_safety():
    ctx = make_context()
    errors_caught: List[Exception] = []

    def worker_thread(index: int):
        try:
            for i in range(50):
                ctx.set_progress(i * 2.0)
                ctx.set_temp_data(f"t{index}_{i}", i)
                ctx.add_error(f"Error thread {index} - {i}")
                ctx.add_warning(f"Warning thread {index} - {i}")
        except Exception as exc:
            errors_caught.append(exc)

    threads = [threading.Thread(target=worker_thread, args=(t,)) for t in range(4)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=5.0)

    assert errors_caught == []
    assert len(ctx.errors) == 200
    assert len(ctx.warnings) == 200
    assert len(ctx.temp_data) == 200
