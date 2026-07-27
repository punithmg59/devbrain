"""
Logical Planner Diagnostics and Audit Collector.
"""

from datetime import datetime, timezone
import threading
from typing import Any, Dict, Optional, Tuple
from pydantic import BaseModel, ConfigDict, Field


class LogicalPlannerDiagnosticItem(BaseModel):
    """
    Immutable diagnostic item produced during logical planning, lowering, or validation.
    """
    model_config = ConfigDict(frozen=True)

    stage: str = Field(..., description="Planner stage (Lowering, Validation, Planning)")
    severity: str = Field(default="INFO", description="Severity level: INFO, WARNING, ERROR")
    message: str = Field(..., description="Diagnostic message string")
    operator_id: Optional[str] = Field(default=None, description="Associated logical operator ID")
    node_ref: Optional[str] = Field(default=None, description="Associated query AST node ID")
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="UTC creation timestamp",
    )
    details: Dict[str, Any] = Field(default_factory=dict, description="Additional context attributes")


class LogicalPlannerDiagnostics:
    """
    Thread-safe collector for logical planner diagnostic events and trace logs.
    """

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._items: list[LogicalPlannerDiagnosticItem] = []

    def record_item(
        self,
        stage: str,
        message: str,
        severity: str = "INFO",
        operator_id: Optional[str] = None,
        node_ref: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Thread-safely records a LogicalPlannerDiagnosticItem."""
        item = LogicalPlannerDiagnosticItem(
            stage=stage,
            severity=severity.upper(),
            message=message,
            operator_id=operator_id,
            node_ref=node_ref,
            details=details or {},
        )
        with self._lock:
            self._items.append(item)

    def get_items(self) -> Tuple[LogicalPlannerDiagnosticItem, ...]:
        """Returns tuple of all recorded diagnostic items."""
        with self._lock:
            return tuple(self._items)

    def has_errors(self) -> bool:
        """Returns True if any ERROR severity item exists."""
        with self._lock:
            return any(item.severity == "ERROR" for item in self._items)

    def count(self) -> int:
        """Returns total count of diagnostic items."""
        with self._lock:
            return len(self._items)


__all__ = [
    "LogicalPlannerDiagnosticItem",
    "LogicalPlannerDiagnostics",
]
