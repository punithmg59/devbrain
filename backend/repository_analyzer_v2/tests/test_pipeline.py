"""tests/test_pipeline.py – Unit tests for Phase 0.6 pipeline framework."""
from __future__ import annotations

from typing import Any, List

import pytest

from pipeline import (
    DiscoveryStage,
    ExtractorStage,
    LinkerStage,
    ParserStage,
    Pipeline,
    PipelineCompletedEvent,
    PipelineContext,
    PipelineError,
    PipelineFailedEvent,
    ReporterStage,
    SchedulerStage,
    Stage,
    StageCompletedEvent,
    StageFailedEvent,
    StageStartedEvent,
    StorageStage,
    ValidatorStage,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

from models.repository import Repository

def make_repo(repo_id: str = "repo-test") -> Repository:
    return Repository(id=repo_id, url="https://github.com/test/repo", name="test-repo")

def make_ctx(run_id: str = "run-test", repo_id: str = "repo-test") -> PipelineContext:
    return PipelineContext(run_id=run_id, repository=make_repo(repo_id))


class SuccessStage(Stage):
    """Minimal passing stage for testing."""
    def __init__(self, label: str = "Success"):
        self._name = label
        self.executed = False

    @property
    def name(self) -> str:
        return self._name

    def setup(self, ctx: PipelineContext) -> None: pass
    def execute(self, ctx: PipelineContext) -> None:
        self.executed = True
    def teardown(self, ctx: PipelineContext) -> None: pass


class FailingStage(Stage):
    """Stage that always raises."""
    @property
    def name(self) -> str:
        return "Failing"

    def setup(self, ctx: PipelineContext) -> None: pass
    def execute(self, ctx: PipelineContext) -> None:
        raise RuntimeError("deliberate failure")
    def teardown(self, ctx: PipelineContext) -> None: pass


class TeardownRecordingStage(Stage):
    """Verifies teardown is called even when execute raises."""
    def __init__(self):
        self.teardown_called = False

    @property
    def name(self) -> str:
        return "TeardownCheck"

    def setup(self, ctx: PipelineContext) -> None: pass
    def execute(self, ctx: PipelineContext) -> None:
        raise RuntimeError("boom")
    def teardown(self, ctx: PipelineContext) -> None:
        self.teardown_called = True


# ---------------------------------------------------------------------------
# Stage interface tests
# ---------------------------------------------------------------------------

def test_stage_executes_and_records_timing():
    stage = SuccessStage()
    ctx = make_ctx()
    stage.run(ctx)
    assert stage.executed
    stage_names = {m.stage_name for m in ctx.metrics}
    assert "Success" in stage_names


def test_stage_emits_started_and_completed_events():
    events: List[Any] = []
    stage = SuccessStage()
    ctx = make_ctx()
    stage.run(ctx, event_bus=events.append)
    types = [type(e) for e in events]
    assert StageStartedEvent in types
    assert StageCompletedEvent in types


def test_stage_emits_failed_event_on_error():
    events: List[Any] = []
    stage = FailingStage()
    ctx = make_ctx()
    with pytest.raises(RuntimeError):
        stage.run(ctx, event_bus=events.append)
    types = [type(e) for e in events]
    assert StageFailedEvent in types
    assert ctx.has_errors  # error message captured


def test_teardown_always_called():
    stage = TeardownRecordingStage()
    ctx = make_ctx()
    with pytest.raises(RuntimeError):
        stage.run(ctx)
    assert stage.teardown_called


# ---------------------------------------------------------------------------
# Pipeline orchestrator tests
# ---------------------------------------------------------------------------

def test_pipeline_full_run_all_default_stages():
    ctx = make_ctx()
    pipeline = Pipeline()
    result = pipeline.run(ctx)
    # All 8 default stages must have recorded timings
    expected_stages = [
        "Discovery", "Scheduler", "Parser", "Extractor",
        "Linker", "Storage", "Validator", "Reporter",
    ]
    stage_names = {m.stage_name for m in result.metrics}
    for name in expected_stages:
        assert name in stage_names, f"Stage '{name}' missing from metrics"


def test_pipeline_emits_completed_event():
    events: List[Any] = []
    pipeline = Pipeline(on_event=events.append)
    pipeline.run(make_ctx())
    assert any(isinstance(e, PipelineCompletedEvent) for e in events)


def test_pipeline_stops_on_first_failure():
    s1 = SuccessStage("S1")
    s2 = FailingStage()
    s3 = SuccessStage("S3")
    pipeline = Pipeline(stages=[s1, s2, s3])
    ctx = make_ctx()
    with pytest.raises(PipelineError) as exc_info:
        pipeline.run(ctx)
    assert exc_info.value.stage_name == "Failing"
    assert not s3.executed  # must not have run


def test_pipeline_emits_failed_event_on_abort():
    events: List[Any] = []
    pipeline = Pipeline(stages=[FailingStage()], on_event=events.append)
    ctx = make_ctx()
    with pytest.raises(PipelineError):
        pipeline.run(ctx)
    assert any(isinstance(e, PipelineFailedEvent) for e in events)


def test_pipeline_context_metadata_passes_between_stages():
    class Writer(Stage):
        @property
        def name(self): return "Writer"
        def setup(self, ctx): pass
        def execute(self, ctx): ctx.metadata["token"] = 42
        def teardown(self, ctx): pass

    class Reader(Stage):
        @property
        def name(self): return "Reader"
        def setup(self, ctx): pass
        def execute(self, ctx): assert ctx.metadata.get("token") == 42
        def teardown(self, ctx): pass

    pipeline = Pipeline(stages=[Writer(), Reader()])
    pipeline.run(make_ctx())  # Would raise AssertionError if metadata not shared


def test_pipeline_custom_stages():
    stages = [SuccessStage(f"Stage{i}") for i in range(4)]
    pipeline = Pipeline(stages=stages)
    ctx = pipeline.run(make_ctx())
    stage_names = {m.stage_name for m in ctx.metrics}
    for i in range(4):
        assert f"Stage{i}" in stage_names


def test_pipeline_error_wraps_original():
    pipeline = Pipeline(stages=[FailingStage()])
    with pytest.raises(PipelineError) as exc_info:
        pipeline.run(make_ctx())
    assert isinstance(exc_info.value.cause, RuntimeError)
    assert "deliberate failure" in str(exc_info.value.cause)


# ---------------------------------------------------------------------------
# Individual stage smoke tests
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("stage_cls", [
    DiscoveryStage,
    SchedulerStage,
    ParserStage,
    ExtractorStage,
    LinkerStage,
    StorageStage,
    ValidatorStage,
    ReporterStage,
])
def test_each_stage_runs_without_error(stage_cls):
    stage = stage_cls()
    ctx = make_ctx()
    stage.run(ctx)
    assert stage.name in {m.stage_name for m in ctx.metrics}
