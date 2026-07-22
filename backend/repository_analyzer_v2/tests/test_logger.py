import io
import json
import logging
import pytest

from utils import (
    ConsoleFormatter,
    JSONFormatter,
    clear_log_context,
    get_logger,
    set_log_context,
    setup_logging,
)


@pytest.fixture(autouse=True)
def reset_logging_context():
    """Reset context and root logger handlers before and after each test."""
    clear_log_context()
    root = logging.getLogger()
    for h in list(root.handlers):
        root.removeHandler(h)
    yield
    clear_log_context()
    for h in list(root.handlers):
        root.removeHandler(h)


def test_json_formatter_basic():
    """Test JSONFormatter output structure."""
    formatter = JSONFormatter()
    record = logging.LogRecord(
        name="test_logger",
        level=logging.INFO,
        pathname="test.py",
        lineno=10,
        msg="Test log message",
        args=(),
        exc_info=None,
    )
    formatted = formatter.format(record)
    data = json.loads(formatted)

    assert data["level"] == "INFO"
    assert data["logger"] == "test_logger"
    assert data["message"] == "Test log message"
    assert "timestamp" in data


def test_json_formatter_structured_fields():
    """Test JSONFormatter with structured context attributes."""
    formatter = JSONFormatter()
    record = logging.LogRecord(
        name="test_logger",
        level=logging.ERROR,
        pathname="test.py",
        lineno=20,
        msg="Error in pipeline",
        args=(),
        exc_info=None,
    )
    record.request_id = "req-123"
    record.analysis_id = "analysis-456"
    record.repository_id = "repo-789"
    record.stage = "Parsing"
    record.duration = 150.5
    record.error = "File parse exception"
    record.warning = "Deprecation warning"

    formatted = formatter.format(record)
    data = json.loads(formatted)

    assert data["request_id"] == "req-123"
    assert data["analysis_id"] == "analysis-456"
    assert data["repository_id"] == "repo-789"
    assert data["stage"] == "Parsing"
    assert data["duration"] == 150.5
    assert data["error"] == "File parse exception"
    assert data["warning"] == "Deprecation warning"


def test_console_formatter_structured_fields():
    """Test ConsoleFormatter annotates message with context fields."""
    formatter = ConsoleFormatter("%(levelname)s: %(message)s")
    record = logging.LogRecord(
        name="test_logger",
        level=logging.INFO,
        pathname="test.py",
        lineno=10,
        msg="Console message",
        args=(),
        exc_info=None,
    )
    record.stage = "Discovery"
    record.repository_id = "repo-abc"

    formatted = formatter.format(record)
    assert "INFO: Console message" in formatted
    assert "stage=Discovery" in formatted
    assert "repository_id=repo-abc" in formatted


def test_set_and_clear_log_context():
    """Test that set_log_context injects values into logs via setup_logging."""
    stream = io.StringIO()
    setup_logging(log_level="INFO", json_format=True, stream=stream)
    logger = get_logger("test_context")

    set_log_context(
        request_id="req-001",
        analysis_id="run-002",
        repository_id="repo-003",
        stage="Extractor",
    )

    logger.info("Processing repository")

    log_output = stream.getvalue().strip()
    data = json.loads(log_output)

    assert data["request_id"] == "req-001"
    assert data["analysis_id"] == "run-002"
    assert data["repository_id"] == "repo-003"
    assert data["stage"] == "Extractor"

    clear_log_context()
    stream.truncate(0)
    stream.seek(0)

    logger.info("Post cleanup log")
    log_output_cleared = stream.getvalue().strip()
    data_cleared = json.loads(log_output_cleared)

    assert "request_id" not in data_cleared
    assert "analysis_id" not in data_cleared
    assert "repository_id" not in data_cleared
    assert "stage" not in data_cleared


def test_log_level_filtering():
    """Test that log_level threshold is respected."""
    stream = io.StringIO()
    setup_logging(log_level="WARNING", json_format=True, stream=stream)
    logger = get_logger("test_level")

    logger.info("Should not appear")
    assert stream.getvalue() == ""

    logger.warning("Warning message")
    log_output = stream.getvalue().strip()
    data = json.loads(log_output)
    assert data["message"] == "Warning message"
    assert data["level"] == "WARNING"


def test_extra_fields_via_logger_call():
    """Test passing extra context directly in logger call."""
    stream = io.StringIO()
    setup_logging(log_level="INFO", json_format=True, stream=stream)
    logger = get_logger("test_extra")

    logger.info("Direct extra log", extra={"duration_ms": 45.2, "warning": "Low disk space"})

    data = json.loads(stream.getvalue().strip())
    assert data["duration_ms"] == 45.2
    assert data["warning"] == "Low disk space"
