"""
PlannerDiagnostics Infrastructure for Event and Stage Collection.
"""

from datetime import datetime, timezone
from enum import StrEnum
import threading
from typing import Any, Mapping, Optional
from pydantic import BaseModel, ConfigDict, Field


class EventLevel(StrEnum):
    """Event severity level for Planner diagnostics."""
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    STAGE_START = "STAGE_START"
    STAGE_END = "STAGE_END"
    TIMING = "TIMING"


class DiagnosticEvent(BaseModel):
    """
    Immutable planner diagnostic event record.
    """
    model_config = ConfigDict(frozen=True)

    level: EventLevel = Field(..., description="INFO, WARNING, ERROR, STAGE_START, STAGE_END, TIMING")
    stage_name: str = Field(default="", description="Name of planning stage")
    message: str = Field(..., description="Event log message string")
    details: Mapping[str, Any] = Field(default_factory=dict, description="Event payload attributes")
    duration_ms: Optional[float] = Field(default=None, description="Stage duration in milliseconds if applicable")
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="UTC timestamp of event creation",
    )


class PlannerDiagnostics:
    """
    Thread-safe collector gathering planner diagnostic events, stage timings, warnings, and trace messages.
    """

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._events: list[DiagnosticEvent] = []

    def record_event(
        self,
        level: EventLevel | str,
        message: str,
        stage_name: str = "",
        details: Optional[dict[str, Any]] = None,
        duration_ms: Optional[float] = None,
    ) -> None:
        """Records a DiagnosticEvent record thread-safely."""
        lvl = EventLevel(str(level).upper()) if isinstance(level, str) else level
        evt = DiagnosticEvent(
            level=lvl,
            stage_name=stage_name,
            message=message,
            details=details or {},
            duration_ms=duration_ms,
        )
        with self._lock:
            self._events.append(evt)

    def get_events(self) -> tuple[DiagnosticEvent, ...]:
        """Returns tuple of all recorded DiagnosticEvent instances."""
        with self._lock:
            return tuple(self._events)

    def count(self) -> int:
        """Returns count of recorded events."""
        with self._lock:
            return len(self._events)

    def has_errors(self) -> bool:
        """Returns True if any ERROR level event exists."""
        with self._lock:
            return any(evt.level == EventLevel.ERROR for evt in self._events)


__all__ = [
    "EventLevel",
    "DiagnosticEvent",
    "PlannerDiagnostics",
]
