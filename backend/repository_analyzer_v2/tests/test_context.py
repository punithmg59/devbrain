"""tests/test_context.py – Unit tests for Phase 0.7 PipelineContext."""
from __future__ import annotations

import threading
import time

import pytest

from models.repository import Repository
from pipeline.context import (
    ContextError,
    ContextWarning,
    PipelineContext,
    Progress,
    RunStatus,
    StageMetrics,
)
from models.analysis import PipelineStage


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def make_repo(**kwargs) -> Repository:
    defaults = dict(id="repo-1", url="https://github.com/test/repo", name="test-repo")
    defaults.update(kwargs)
    return Repository(**defaults)


def make_ctx(run_id: str = "run-1", **repo_kwargs) -> PipelineContext:
    return PipelineContext(run_id=run_id, repository=make_repo(**repo_kwargs))


# ---------------------------------------------------------------------------
# Immutable identity
# ---------------------------------------------------------------------------

def test_run_id_is_immutable():
    ctx = make_ctx(run_id="abc-123")
    assert ctx.run_id == "abc-123"
    with pytest.raises(AttributeError):
        ctx.run_id = "other"  # type: ignore[misc]


def test_repository_is_immutable():
    ctx = make_ctx()
    assert ctx.repository.id == "repo-1"
    with pytest.raises(AttributeError):
        ctx.repository = make_repo(id="other")  # type: ignore[misc]


def test_started_at_is_immutable():
    ctx = make_ctx()
    ts = ctx.started_at
    with pytest.raises(AttributeError):
        ctx.started_at = ts  # type: ignore[misc]


def test_repository_id_convenience():
    ctx = make_ctx()
    assert ctx.repository_id == ctx.repository.id


# ---------------------------------------------------------------------------
# Status lifecycle
# ---------------------------------------------------------------------------

def test_initial_status_is_pending():
    ctx = make_ctx()
    assert ctx.status == RunStatus.PENDING


def test_start_transitions_to_running():
    ctx = make_ctx()
    ctx.start()
    assert ctx.status == RunStatus.RUNNING


def test_start_twice_raises():
    ctx = make_ctx()
    ctx.start()
    with pytest.raises(RuntimeError, match="Cannot start"):
        ctx.start()


def test_mark_completed():
    ctx = make_ctx()
    ctx.start()
    ctx.mark_completed()
    assert ctx.status == RunStatus.COMPLETED
    assert ctx.ended_at is not None


def test_mark_failed():
    ctx = make_ctx()
    ctx.start()
    ctx.mark_failed()
    assert ctx.status == RunStatus.FAILED
    assert ctx.ended_at is not None


def test_mark_completed_is_idempotent():
    ctx = make_ctx()
    ctx.start()
    ctx.mark_completed()
    first_end = ctx.ended_at
    ctx.mark_completed()  # should not raise or overwrite
    assert ctx.ended_at == first_end


def test_mark_failed_is_idempotent():
    ctx = make_ctx()
    ctx.start()
    ctx.mark_failed()
    first_end = ctx.ended_at
    ctx.mark_failed()
    assert ctx.ended_at == first_end


# ---------------------------------------------------------------------------
# Stage & file tracking
# ---------------------------------------------------------------------------

def test_advance_stage():
    ctx = make_ctx()
    assert ctx.current_stage is None
    ctx.advance_stage(PipelineStage.PARSING)
    assert ctx.current_stage == PipelineStage.PARSING


def test_advance_stage_clears_current_file():
    ctx = make_ctx()
    ctx.set_current_file("src/main.py")
    ctx.advance_stage(PipelineStage.EXTRACTION)
    assert ctx.current_file is None


def test_set_current_file():
    ctx = make_ctx()
    ctx.set_current_file("src/utils.py")
    assert ctx.current_file == "src/utils.py"
    ctx.set_current_file(None)
    assert ctx.current_file is None


# ---------------------------------------------------------------------------
# Errors & Warnings
# ---------------------------------------------------------------------------

def test_add_error():
    ctx = make_ctx()
    ctx.add_error("Parser", "Syntax error", exc_type="SyntaxError", file_path="bad.py")
    errors = ctx.errors
    assert len(errors) == 1
    assert isinstance(errors[0], ContextError)
    assert errors[0].stage_name == "Parser"
    assert errors[0].exc_type == "SyntaxError"
    assert errors[0].file_path == "bad.py"


def test_add_warning():
    ctx = make_ctx()
    ctx.add_warning("Extractor", "Skipped empty file", file_path="empty.py")
    warnings = ctx.warnings
    assert len(warnings) == 1
    assert isinstance(warnings[0], ContextWarning)
    assert warnings[0].file_path == "empty.py"


def test_has_errors_and_warnings():
    ctx = make_ctx()
    assert not ctx.has_errors
    assert not ctx.has_warnings
    ctx.add_error("S", "err")
    assert ctx.has_errors
    ctx.add_warning("S", "warn")
    assert ctx.has_warnings


def test_errors_returns_copy():
    """Mutating the returned list must not affect internal state."""
    ctx = make_ctx()
    ctx.add_error("S", "e1")
    snapshot = ctx.errors
    snapshot.clear()
    assert len(ctx.errors) == 1


# ---------------------------------------------------------------------------
# Metrics
# ---------------------------------------------------------------------------

def test_record_metrics():
    ctx = make_ctx()
    ctx.record_metrics(StageMetrics(stage_name="Discovery", duration_ms=42.5))
    metrics = ctx.metrics
    assert len(metrics) == 1
    assert metrics[0].stage_name == "Discovery"
    assert metrics[0].duration_ms == 42.5


def test_total_duration_ms():
    ctx = make_ctx()
    ctx.record_metrics(StageMetrics("A", duration_ms=100.0))
    ctx.record_metrics(StageMetrics("B", duration_ms=200.0))
    assert ctx.total_duration_ms == 300.0


def test_stage_metrics_is_frozen():
    m = StageMetrics(stage_name="X", duration_ms=10.0)
    with pytest.raises((AttributeError, TypeError)):
        m.duration_ms = 99.0  # type: ignore[misc]


# ---------------------------------------------------------------------------
# Progress
# ---------------------------------------------------------------------------

def test_progress_default():
    p = Progress()
    assert p.percentage == 0.0
    assert p.total_files == 0


def test_progress_percentage():
    p = Progress(total_files=10)
    p.increment(5)
    assert p.percentage == 50.0


def test_progress_increment_clamps():
    p = Progress(total_files=5)
    p.increment(100)
    assert p.processed_files == 5
    assert p.percentage == 100.0


def test_progress_zero_total_files():
    p = Progress(total_files=0)
    assert p.percentage == 0.0


# ---------------------------------------------------------------------------
# Thread safety
# ---------------------------------------------------------------------------

def test_thread_safe_error_recording():
    ctx = make_ctx()
    errors_to_add = 200

    def add_errors():
        for i in range(errors_to_add // 10):
            ctx.add_error("ThreadStage", f"err-{i}")

    threads = [threading.Thread(target=add_errors) for _ in range(10)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert len(ctx.errors) == errors_to_add


# ---------------------------------------------------------------------------
# Computed helpers
# ---------------------------------------------------------------------------

def test_elapsed_seconds_increases():
    ctx = make_ctx()
    ctx.start()
    time.sleep(0.05)
    assert ctx.elapsed_seconds >= 0.04


def test_elapsed_seconds_frozen_after_completion():
    ctx = make_ctx()
    ctx.start()
    ctx.mark_completed()
    t1 = ctx.elapsed_seconds
    time.sleep(0.05)
    t2 = ctx.elapsed_seconds
    assert abs(t1 - t2) < 0.01  # should not grow after completion


def test_repr_contains_key_info():
    ctx = make_ctx(run_id="r99")
    r = repr(ctx)
    assert "r99" in r
    assert "pending" in r


# ---------------------------------------------------------------------------
# Full pipeline integration with rich context
# ---------------------------------------------------------------------------

def test_pipeline_run_uses_rich_context():
    from pipeline import Pipeline

    repo = make_repo()
    ctx = PipelineContext(run_id="int-run", repository=repo)
    pipeline = Pipeline()
    result = pipeline.run(ctx)

    assert result.status == RunStatus.COMPLETED
    assert result.ended_at is not None
    # All 8 default stages should have recorded StageMetrics
    stage_names = {m.stage_name for m in result.metrics}
    for expected in ["Discovery", "Scheduler", "Parser", "Extractor",
                     "Linker", "Storage", "Validator", "Reporter"]:
        assert expected in stage_names
