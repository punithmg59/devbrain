"""
Logging Models and Enums for Graph Query Engine.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import StrEnum
from typing import Any, Optional

from graph_query_engine.types import CorrelationId, RequestId


class LogLevel(StrEnum):
    """
    Standard log levels.
    """
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


@dataclass(frozen=True)
class LogContext:
    """
    Key-value pairs for contextual log metadata.
    """
    correlation_id: Optional[CorrelationId] = None
    request_id: Optional[RequestId] = None
    query_id: Optional[str] = None
    component: Optional[str] = None
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class StructuredLog:
    """
    Immutable representation of a structured log record.
    """
    level: LogLevel
    message: str
    logger_name: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    context: Optional[LogContext] = None
    exception: Optional[BaseException] = None
    stack_info: Optional[str] = None
