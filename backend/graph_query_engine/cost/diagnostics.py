"""
Cost Diagnostics Collector.

Captures traces, warnings, statistics used, and confidence scoring breakdowns.
"""

from datetime import datetime, timezone
import threading
from typing import Any, Dict, List, Optional, Tuple
from pydantic import BaseModel, ConfigDict, Field


class CostDiagnosticItem(BaseModel):
    """
    Immutable diagnostic item produced during cost estimation.
    """
    model_config = ConfigDict(frozen=True)

    stage: str = Field(default="CostEstimation", description="Stage name")
    severity: str = Field(default="INFO", description="Severity level: INFO, WARNING, ERROR")
    message: str = Field(..., description="Diagnostic message string")
    operator_id: Optional[str] = Field(default=None, description="Associated operator ID")
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="UTC creation timestamp",
    )


class CostDiagnostics:
    """
    Thread-safe diagnostics collector for cost model estimation passes.
    """

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._items: List[CostDiagnosticItem] = []
        self._warnings: List[str] = []

    def record_trace(self, message: str, operator_id: Optional[str] = None) -> None:
        """Records an informational cost estimation trace."""
        item = CostDiagnosticItem(stage="CostEstimation", severity="INFO", message=message, operator_id=operator_id)
        with self._lock:
            self._items.append(item)

    def record_warning(self, message: str, operator_id: Optional[str] = None) -> None:
        """Records a warning during cost estimation."""
        item = CostDiagnosticItem(stage="CostEstimation", severity="WARNING", message=message, operator_id=operator_id)
        with self._lock:
            self._items.append(item)
            self._warnings.append(message)

    def get_traces(self) -> Tuple[str, ...]:
        """Returns tuple of all trace message strings."""
        with self._lock:
            return tuple(f"[{i.severity}] {i.message}" for i in self._items)

    def get_warnings(self) -> Tuple[str, ...]:
        """Returns tuple of all warning strings."""
        with self._lock:
            return tuple(self._warnings)


__all__ = [
    "CostDiagnosticItem",
    "CostDiagnostics",
]
