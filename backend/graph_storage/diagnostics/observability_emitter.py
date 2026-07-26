"""
ObservabilityEmitter abstract interface.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional


class ObservabilityEmitter(ABC):
    """Abstract interface for unified metric, event, log, and trace observability."""

    @abstractmethod
    def emit_metric(self, name: str, value: float, tags: Optional[Dict[str, str]] = None) -> None:
        """Emit a numerical metric datapoint."""
        ...

    @abstractmethod
    def emit_event(self, name: str, payload: Dict[str, Any]) -> None:
        """Emit a structured domain or storage event."""
        ...

    @abstractmethod
    def emit_log(self, level: str, message: str, context: Optional[Dict[str, Any]] = None) -> None:
        """Emit a structured diagnostic log record."""
        ...

    @abstractmethod
    def begin_trace(self, name: str) -> str:
        """Begin an execution trace context and return a trace ID."""
        ...

    @abstractmethod
    def end_trace(self, trace_id: str) -> None:
        """End an active trace context given its trace ID."""
        ...
