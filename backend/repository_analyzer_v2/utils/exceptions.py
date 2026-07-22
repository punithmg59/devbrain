"""
utils/exceptions.py
-------------------
Canonical exception hierarchy for the DevBrain Repository Analyzer V2.

Design principles
-----------------
* All domain exceptions derive from ``AnalyzerBaseError`` so callers can
  catch the entire hierarchy with a single ``except AnalyzerBaseError``.
* Every exception carries rich metadata: an ``ErrorCode``, free-form
  ``context`` dict, optional ``file_path``, optional ``stage_name``, and
  an auto-captured formatted traceback.
* Logging integration: call ``.log(logger)`` on any exception to emit a
  fully structured ERROR record automatically.
"""
from __future__ import annotations

import logging
import traceback
from enum import Enum
from typing import Any, Dict, Optional


# ---------------------------------------------------------------------------
# Error codes
# ---------------------------------------------------------------------------

class ErrorCode(str, Enum):
    """Canonical error codes for the analyzer. Prefix maps to subsystem."""

    # Generic
    UNKNOWN                = "ANALYZER_001"

    # Repository
    REPO_NOT_FOUND         = "REPO_001"
    REPO_CLONE_FAILED      = "REPO_002"
    REPO_INVALID_URL       = "REPO_003"
    REPO_ACCESS_DENIED     = "REPO_004"

    # Plugin
    PLUGIN_NOT_FOUND       = "PLUGIN_001"
    PLUGIN_DUPLICATE       = "PLUGIN_002"
    PLUGIN_INIT_FAILED     = "PLUGIN_003"
    PLUGIN_VERSION_INVALID = "PLUGIN_004"

    # Pipeline
    PIPELINE_STAGE_FAILED  = "PIPELINE_001"
    PIPELINE_ABORTED       = "PIPELINE_002"
    PIPELINE_TIMEOUT       = "PIPELINE_003"

    # Parser
    PARSER_SYNTAX_ERROR    = "PARSER_001"
    PARSER_UNSUPPORTED     = "PARSER_002"
    PARSER_TIMEOUT         = "PARSER_003"
    PARSER_ENCODING_ERROR  = "PARSER_004"

    # Storage
    STORAGE_WRITE_FAILED   = "STORAGE_001"
    STORAGE_READ_FAILED    = "STORAGE_002"
    STORAGE_CONNECTION     = "STORAGE_003"
    STORAGE_MIGRATION      = "STORAGE_004"

    # Validation
    VALIDATION_SCHEMA      = "VALIDATION_001"
    VALIDATION_GRAPH       = "VALIDATION_002"
    VALIDATION_CONSTRAINT  = "VALIDATION_003"

    # Worker
    WORKER_LIMIT_EXCEEDED  = "WORKER_001"
    WORKER_CRASH           = "WORKER_002"
    WORKER_TIMEOUT         = "WORKER_003"

    # Configuration
    CONFIG_MISSING_KEY     = "CONFIG_001"
    CONFIG_INVALID_VALUE   = "CONFIG_002"
    CONFIG_ENV_NOT_SET     = "CONFIG_003"

    # Scheduler (Phase 2.2)
    SCHEDULER_JOB_NOT_FOUND       = "SCHEDULER_001"
    SCHEDULER_DUPLICATE_JOB       = "SCHEDULER_002"
    SCHEDULER_INVALID_TRANSITION  = "SCHEDULER_003"
    SCHEDULER_RETRY_EXHAUSTED     = "SCHEDULER_004"


# ---------------------------------------------------------------------------
# Base exception
# ---------------------------------------------------------------------------

class AnalyzerBaseError(Exception):
    """
    Base class for all Repository Analyzer exceptions.

    Attributes
    ----------
    code        : ErrorCode – machine-readable code for the subsystem.
    message     : str       – human-readable description.
    context     : dict      – arbitrary key-value pairs for debugging.
    file_path   : str | None – relevant source file, if any.
    stage_name  : str | None – pipeline stage where the error occurred.
    traceback   : str | None – formatted traceback captured at raise time.
    cause       : Exception | None – chained original exception.
    """

    def __init__(
        self,
        message: str,
        code: ErrorCode = ErrorCode.UNKNOWN,
        context: Optional[Dict[str, Any]] = None,
        file_path: Optional[str] = None,
        stage_name: Optional[str] = None,
        cause: Optional[Exception] = None,
    ) -> None:
        super().__init__(message)
        self.message: str = message
        self.code: ErrorCode = code
        self.context: Dict[str, Any] = context or {}
        self.file_path: Optional[str] = file_path
        self.stage_name: Optional[str] = stage_name
        self.cause: Optional[Exception] = cause

        # Capture formatted traceback for the cause (if provided)
        if cause is not None:
            self.traceback: Optional[str] = "".join(
                traceback.format_exception(type(cause), cause, cause.__traceback__)
            )
        else:
            self.traceback = None

    # ------------------------------------------------------------------
    # Logging integration
    # ------------------------------------------------------------------

    def log(self, logger: logging.Logger, level: int = logging.ERROR) -> None:
        """
        Emit a structured log record for this exception using *logger*.

        All metadata fields are passed as ``extra`` so structured
        formatters (e.g. JSONFormatter) can include them.
        """
        extra: Dict[str, Any] = {
            "error_code": self.code.value,
            "error": self.message,
        }
        if self.file_path:
            extra["file_path"] = self.file_path
        if self.stage_name:
            extra["stage"] = self.stage_name
        if self.context:
            extra["context"] = self.context
        if self.traceback:
            extra["traceback"] = self.traceback

        logger.log(level, self.message, extra=extra)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def to_dict(self) -> Dict[str, Any]:
        """Serialise the exception to a plain dict (useful for API responses)."""
        return {
            "error_code": self.code.value,
            "message": self.message,
            "context": self.context,
            "file_path": self.file_path,
            "stage_name": self.stage_name,
            "cause": str(self.cause) if self.cause else None,
        }

    def __repr__(self) -> str:
        return (
            f"{type(self).__name__}("
            f"code={self.code.value!r}, "
            f"message={self.message!r}, "
            f"stage={self.stage_name!r})"
        )


# ---------------------------------------------------------------------------
# Domain-specific exceptions
# ---------------------------------------------------------------------------

class RepositoryError(AnalyzerBaseError):
    """
    Raised when a repository-level operation fails.

    Examples: invalid URL, failed clone, missing manifest.
    """
    def __init__(
        self,
        message: str,
        code: ErrorCode = ErrorCode.REPO_NOT_FOUND,
        **kwargs: Any,
    ) -> None:
        super().__init__(message, code=code, **kwargs)


class PluginError(AnalyzerBaseError):
    """
    Raised for plugin lifecycle failures.

    Examples: duplicate registration, failed initialisation, unsupported version.
    """
    def __init__(
        self,
        message: str,
        code: ErrorCode = ErrorCode.PLUGIN_NOT_FOUND,
        **kwargs: Any,
    ) -> None:
        super().__init__(message, code=code, **kwargs)


class PipelineError(AnalyzerBaseError):
    """
    Raised when a pipeline stage fails and halts the run.

    Carries *stage_name* and the original *cause* exception.
    """
    def __init__(
        self,
        message: str,
        code: ErrorCode = ErrorCode.PIPELINE_STAGE_FAILED,
        *,
        stage_name: Optional[str] = None,
        cause: Optional[Exception] = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(message, code=code, stage_name=stage_name, cause=cause, **kwargs)


class ParserError(AnalyzerBaseError):
    """
    Raised when a language plugin cannot parse a source file.

    Examples: syntax error, unsupported encoding, parse timeout.
    """
    def __init__(
        self,
        message: str,
        code: ErrorCode = ErrorCode.PARSER_SYNTAX_ERROR,
        **kwargs: Any,
    ) -> None:
        super().__init__(message, code=code, **kwargs)


class StorageError(AnalyzerBaseError):
    """
    Raised when persistence operations (read, write, migration) fail.
    """
    def __init__(
        self,
        message: str,
        code: ErrorCode = ErrorCode.STORAGE_WRITE_FAILED,
        **kwargs: Any,
    ) -> None:
        super().__init__(message, code=code, **kwargs)


class ValidationError(AnalyzerBaseError):
    """
    Raised when graph or schema validation detects inconsistencies.

    Examples: orphan nodes, duplicate IDs, missing required fields.
    """
    def __init__(
        self,
        message: str,
        code: ErrorCode = ErrorCode.VALIDATION_SCHEMA,
        **kwargs: Any,
    ) -> None:
        super().__init__(message, code=code, **kwargs)


class WorkerError(AnalyzerBaseError):
    """
    Raised when a worker process or thread fails.

    Examples: worker crash, pool exhausted, processing timeout.
    """
    def __init__(
        self,
        message: str,
        code: ErrorCode = ErrorCode.WORKER_CRASH,
        **kwargs: Any,
    ) -> None:
        super().__init__(message, code=code, **kwargs)


class ConfigurationError(AnalyzerBaseError):
    """
    Raised when the application cannot load or validate its configuration.

    Examples: missing env var, invalid type, out-of-range value.
    """
    def __init__(
        self,
        message: str,
        code: ErrorCode = ErrorCode.CONFIG_MISSING_KEY,
        **kwargs: Any,
    ) -> None:
        super().__init__(message, code=code, **kwargs)


class SchedulerError(AnalyzerBaseError):
    """
    Raised when the Analysis Job Scheduler detects an illegal operation.

    Examples: submitting a duplicate job, illegal status transition,
    retrying a job that has exhausted its retry budget.
    """
    def __init__(
        self,
        message: str,
        code: ErrorCode = ErrorCode.SCHEDULER_JOB_NOT_FOUND,
        **kwargs: Any,
    ) -> None:
        super().__init__(message, code=code, **kwargs)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

__all__ = [
    "ErrorCode",
    "AnalyzerBaseError",
    "RepositoryError",
    "PluginError",
    "PipelineError",
    "ParserError",
    "StorageError",
    "ValidationError",
    "WorkerError",
    "ConfigurationError",
    "SchedulerError",
]
