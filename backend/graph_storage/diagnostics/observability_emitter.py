"""
ObservabilityEmitter abstract interface.
"""

from abc import ABC, abstractmethod
from graph_storage.model import MetricRecord, StorageEvent, LogRecord, TraceContext


class ObservabilityEmitter(ABC):
    """Abstract interface for unified metric, event, log, and trace observability."""

    @abstractmethod
    def emit_metric(self, record: MetricRecord) -> None:
        """Emit a structured numerical metric record."""
        ...

    @abstractmethod
    def emit_event(self, event: StorageEvent) -> None:
        """Emit a structured domain storage event."""
        ...

    @abstractmethod
    def emit_log(self, record: LogRecord) -> None:
        """Emit a structured diagnostic log record."""
        ...

    @abstractmethod
    def begin_trace(self, name: str) -> TraceContext:
        """Begin an execution trace span and return its tracing context."""
        ...

    @abstractmethod
    def end_trace(self, context: TraceContext) -> None:
        """End an active tracing context."""
        ...
