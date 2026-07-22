import contextvars
import json
import logging
import sys
from datetime import datetime, timezone
from typing import Any, Dict, Optional

# ContextVars for thread-safe/async-safe context tracking
request_id_ctx: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar("request_id", default=None)
analysis_id_ctx: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar("analysis_id", default=None)
repository_id_ctx: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar("repository_id", default=None)
stage_ctx: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar("stage", default=None)


def set_log_context(
    request_id: Optional[str] = None,
    analysis_id: Optional[str] = None,
    repository_id: Optional[str] = None,
    stage: Optional[str] = None,
) -> None:
    """Set contextual fields in ContextVars for structured logging."""
    if request_id is not None:
        request_id_ctx.set(request_id)
    if analysis_id is not None:
        analysis_id_ctx.set(analysis_id)
    if repository_id is not None:
        repository_id_ctx.set(repository_id)
    if stage is not None:
        stage_ctx.set(stage)


def clear_log_context() -> None:
    """Clear all contextual fields in ContextVars."""
    request_id_ctx.set(None)
    analysis_id_ctx.set(None)
    repository_id_ctx.set(None)
    stage_ctx.set(None)


class StructuredLogFilter(logging.Filter):
    """Logging filter that injects contextual attributes into every LogRecord."""

    def filter(self, record: logging.LogRecord) -> bool:
        if not hasattr(record, "request_id") or record.request_id is None:
            record.request_id = request_id_ctx.get()
        if not hasattr(record, "analysis_id") or record.analysis_id is None:
            record.analysis_id = analysis_id_ctx.get()
        if not hasattr(record, "repository_id") or record.repository_id is None:
            record.repository_id = repository_id_ctx.get()
        if not hasattr(record, "stage") or record.stage is None:
            record.stage = stage_ctx.get()
        return True


class JSONFormatter(logging.Formatter):
    """Formatter that converts a LogRecord into a JSON string with structured metadata."""

    def format(self, record: logging.LogRecord) -> str:
        log_data: Dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Check for structured context fields
        context_fields = [
            "request_id",
            "analysis_id",
            "repository_id",
            "stage",
            "duration",
            "duration_ms",
            "error",
            "warning",
            # Exception hierarchy metadata (Phase 0.9)
            "error_code",
            "file_path",
            "context",
            "traceback",
        ]
        for field in context_fields:
            val = getattr(record, field, None)
            if val is not None:
                log_data[field] = val

        if record.exc_info and "error" not in log_data:
            log_data["error"] = self.formatException(record.exc_info)

        return json.dumps(log_data)


class ConsoleFormatter(logging.Formatter):
    """Formatter that outputs human-readable logs annotated with structured context."""

    def format(self, record: logging.LogRecord) -> str:
        base_msg = super().format(record)
        context_parts = []
        context_fields = [
            "request_id",
            "analysis_id",
            "repository_id",
            "stage",
            "duration",
            "duration_ms",
            "error",
            "warning",
        ]
        for field in context_fields:
            val = getattr(record, field, None)
            if val is not None:
                context_parts.append(f"{field}={val}")
        if context_parts:
            base_msg += f" [{', '.join(context_parts)}]"
        return base_msg


def setup_logging(
    log_level: str = "INFO",
    json_format: bool = True,
    stream: Any = sys.stdout,
) -> logging.Logger:
    """
    Configures the root logger with structured formatters and handlers.
    Returns the configured root logger.
    """
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level.upper())

    # Remove existing handlers to avoid duplicate log entries
    for handler in list(root_logger.handlers):
        root_logger.removeHandler(handler)

    handler = logging.StreamHandler(stream)
    if json_format:
        handler.setFormatter(JSONFormatter())
    else:
        handler.setFormatter(
            ConsoleFormatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
        )

    handler.addFilter(StructuredLogFilter())
    root_logger.addHandler(handler)
    return root_logger


def get_logger(name: str) -> logging.Logger:
    """
    Logger factory function.
    """
    return logging.getLogger(name)
