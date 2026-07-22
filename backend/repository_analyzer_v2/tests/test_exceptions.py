"""tests/test_exceptions.py – Unit tests for Phase 0.9 exception hierarchy."""
from __future__ import annotations

import io
import json
import logging

import pytest

from utils.exceptions import (
    AnalyzerBaseError,
    ConfigurationError,
    ErrorCode,
    ParserError,
    PipelineError,
    PluginError,
    RepositoryError,
    StorageError,
    ValidationError,
    WorkerError,
)
from utils import setup_logging


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_logger(stream: io.StringIO) -> logging.Logger:
    setup_logging(log_level="DEBUG", json_format=True, stream=stream)
    return logging.getLogger("test_exc")


# ---------------------------------------------------------------------------
# Error codes
# ---------------------------------------------------------------------------

def test_all_error_codes_unique():
    """Every ErrorCode value must be unique."""
    values = [e.value for e in ErrorCode]
    assert len(values) == len(set(values)), "Duplicate ErrorCode values found"


def test_error_codes_have_subsystem_prefix():
    """Each ErrorCode value should follow the SUBSYSTEM_NNN pattern."""
    import re
    pattern = re.compile(r"^[A-Z_]+_\d+$")
    for code in ErrorCode:
        assert pattern.match(code.value), f"ErrorCode '{code.value}' does not match pattern"


# ---------------------------------------------------------------------------
# AnalyzerBaseError
# ---------------------------------------------------------------------------

def test_base_error_default_code():
    err = AnalyzerBaseError("Something went wrong")
    assert err.code == ErrorCode.UNKNOWN
    assert err.message == "Something went wrong"
    assert err.context == {}
    assert err.file_path is None
    assert err.stage_name is None
    assert err.cause is None
    assert err.traceback is None


def test_base_error_full_metadata():
    cause = ValueError("root cause")
    err = AnalyzerBaseError(
        "Test error",
        code=ErrorCode.REPO_NOT_FOUND,
        context={"key": "value", "count": 3},
        file_path="src/main.py",
        stage_name="Parser",
        cause=cause,
    )
    assert err.code == ErrorCode.REPO_NOT_FOUND
    assert err.file_path == "src/main.py"
    assert err.stage_name == "Parser"
    assert err.cause is cause
    assert err.context["key"] == "value"
    assert err.traceback is not None
    assert "ValueError" in err.traceback


def test_base_error_inherits_from_exception():
    err = AnalyzerBaseError("err")
    assert isinstance(err, Exception)


def test_base_error_to_dict():
    cause = RuntimeError("boom")
    err = AnalyzerBaseError(
        "dict test",
        code=ErrorCode.PARSER_SYNTAX_ERROR,
        context={"line": 42},
        file_path="bad.py",
        stage_name="Parsing",
        cause=cause,
    )
    d = err.to_dict()
    assert d["error_code"] == ErrorCode.PARSER_SYNTAX_ERROR.value
    assert d["message"] == "dict test"
    assert d["file_path"] == "bad.py"
    assert d["stage_name"] == "Parsing"
    assert d["context"]["line"] == 42
    assert "RuntimeError" in d["cause"] or "boom" in d["cause"]


def test_base_error_repr():
    err = AnalyzerBaseError("oops", code=ErrorCode.WORKER_CRASH, stage_name="Extractor")
    r = repr(err)
    assert "AnalyzerBaseError" in r
    assert "WORKER_002" in r
    assert "Extractor" in r


# ---------------------------------------------------------------------------
# Logging integration
# ---------------------------------------------------------------------------

def test_log_emits_structured_error_record():
    stream = io.StringIO()
    logger = make_logger(stream)
    err = AnalyzerBaseError(
        "log test",
        code=ErrorCode.STORAGE_WRITE_FAILED,
        stage_name="Storage",
        file_path="db/write.py",
        context={"rows": 10},
    )
    err.log(logger)

    output = stream.getvalue().strip()
    assert output, "Expected log output but got nothing"
    data = json.loads(output)
    assert data["message"] == "log test"
    assert data["error_code"] == ErrorCode.STORAGE_WRITE_FAILED.value
    assert data["stage"] == "Storage"
    assert data["file_path"] == "db/write.py"


def test_log_respects_level():
    stream = io.StringIO()
    logger = make_logger(stream)
    err = AnalyzerBaseError("warning-level log")
    err.log(logger, level=logging.WARNING)

    data = json.loads(stream.getvalue().strip())
    assert data["level"] == "WARNING"


def test_log_includes_traceback_for_chained_cause():
    stream = io.StringIO()
    logger = make_logger(stream)
    try:
        raise ZeroDivisionError("division by zero")
    except ZeroDivisionError as e:
        err = AnalyzerBaseError("chained", cause=e)
    err.log(logger)

    data = json.loads(stream.getvalue().strip())
    assert "traceback" in data
    assert "ZeroDivisionError" in data["traceback"]


# ---------------------------------------------------------------------------
# Domain-specific exception defaults
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("exc_cls,expected_code", [
    (RepositoryError,   ErrorCode.REPO_NOT_FOUND),
    (PluginError,       ErrorCode.PLUGIN_NOT_FOUND),
    (PipelineError,     ErrorCode.PIPELINE_STAGE_FAILED),
    (ParserError,       ErrorCode.PARSER_SYNTAX_ERROR),
    (StorageError,      ErrorCode.STORAGE_WRITE_FAILED),
    (ValidationError,   ErrorCode.VALIDATION_SCHEMA),
    (WorkerError,       ErrorCode.WORKER_CRASH),
    (ConfigurationError,ErrorCode.CONFIG_MISSING_KEY),
])
def test_domain_exception_default_code(exc_cls, expected_code):
    err = exc_cls("test msg")
    assert err.code == expected_code
    assert isinstance(err, AnalyzerBaseError)
    assert isinstance(err, Exception)


# ---------------------------------------------------------------------------
# Domain-specific – custom codes
# ---------------------------------------------------------------------------

def test_repository_error_custom_code():
    err = RepositoryError("bad clone", code=ErrorCode.REPO_CLONE_FAILED)
    assert err.code == ErrorCode.REPO_CLONE_FAILED


def test_plugin_error_custom_code():
    err = PluginError("duplicate", code=ErrorCode.PLUGIN_DUPLICATE)
    assert err.code == ErrorCode.PLUGIN_DUPLICATE


def test_pipeline_error_stage_name():
    err = PipelineError("stage fail", stage_name="Extractor")
    assert err.stage_name == "Extractor"
    assert err.code == ErrorCode.PIPELINE_STAGE_FAILED


def test_pipeline_error_cause():
    root = IOError("disk full")
    err = PipelineError("storage fail", stage_name="Storage", cause=root)
    assert err.cause is root
    assert err.traceback is not None


def test_parser_error_with_file_path():
    err = ParserError("syntax error", file_path="src/app.py", code=ErrorCode.PARSER_SYNTAX_ERROR)
    assert err.file_path == "src/app.py"


def test_configuration_error_context():
    err = ConfigurationError("missing env", context={"var": "DATABASE_URL"})
    assert err.context["var"] == "DATABASE_URL"


# ---------------------------------------------------------------------------
# Catchability – base catches all subtypes
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("exc_cls", [
    RepositoryError, PluginError, PipelineError, ParserError,
    StorageError, ValidationError, WorkerError, ConfigurationError,
])
def test_all_caught_by_base(exc_cls):
    with pytest.raises(AnalyzerBaseError):
        raise exc_cls("test")


# ---------------------------------------------------------------------------
# Integration: pipeline raises canonical PipelineError
# ---------------------------------------------------------------------------

def test_pipeline_raises_canonical_error():
    from pipeline import Pipeline, PipelineContext
    from models.repository import Repository

    repo = Repository(id="r1", url="https://example.com/repo", name="repo")
    ctx = PipelineContext(run_id="run-err", repository=repo)

    class BoomStage:
        name = "Boom"
        def setup(self, ctx): pass
        def execute(self, ctx): raise RuntimeError("boom!")
        def teardown(self, ctx): pass
        def run(self, ctx, event_bus=None):
            try:
                self.execute(ctx)
            except Exception as exc:
                raise PipelineError(
                    f"Pipeline failed at stage '{self.name}': {exc}",
                    stage_name=self.name,
                    cause=exc,
                ) from exc

    pipeline = Pipeline(stages=[BoomStage()])

    with pytest.raises(PipelineError) as exc_info:
        pipeline.run(ctx)

    err = exc_info.value
    assert isinstance(err, AnalyzerBaseError)
    assert err.stage_name == "Boom"
    assert "boom!" in str(err.cause)
