"""
Logger Protocol Definitions for Graph Query Engine.
"""

from typing import Any, Optional, Protocol

from graph_query_engine.logging.models import LogContext, LogLevel


class Logger(Protocol):
    """
    Contract for structured logging instances.
    """

    def debug(
        self,
        msg: str,
        context: Optional[LogContext] = None,
        **kwargs: Any,
    ) -> None:
        """Logs a message with level DEBUG."""
        ...

    def info(
        self,
        msg: str,
        context: Optional[LogContext] = None,
        **kwargs: Any,
    ) -> None:
        """Logs a message with level INFO."""
        ...

    def warning(
        self,
        msg: str,
        context: Optional[LogContext] = None,
        **kwargs: Any,
    ) -> None:
        """Logs a message with level WARNING."""
        ...

    def error(
        self,
        msg: str,
        context: Optional[LogContext] = None,
        exc_info: Optional[BaseException] = None,
        **kwargs: Any,
    ) -> None:
        """Logs a message with level ERROR."""
        ...

    def critical(
        self,
        msg: str,
        context: Optional[LogContext] = None,
        exc_info: Optional[BaseException] = None,
        **kwargs: Any,
    ) -> None:
        """Logs a message with level CRITICAL."""
        ...

    def is_enabled_for(self, level: LogLevel) -> bool:
        """Checks if log level is currently enabled."""
        ...


class LoggerFactory(Protocol):
    """
    Contract for constructing Logger instances by name or component.
    """

    def get_logger(self, name: str) -> Logger:
        """
        Retrieves or creates a named Logger instance.
        """
        ...
