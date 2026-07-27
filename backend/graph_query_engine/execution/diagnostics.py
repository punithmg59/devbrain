"""
Execution Planner Diagnostics Subsystem.

Collects audit logs, stage creation traces, dependency ordering, and metadata allocation.
"""

from datetime import datetime, timezone
import threading
from typing import Any, Dict, List, Optional, Tuple
from pydantic import BaseModel, ConfigDict, Field


class ExecutionPlannerDiagnosticItem(BaseModel):
    """
    Immutable diagnostic item logged during execution plan construction.
    """
    model_config = ConfigDict(frozen=True)

    stage: str = Field(default="ExecutionPlanning", description="Planning stage identifier")
    severity: str = Field(default="INFO", description="Severity: INFO, WARNING, ERROR")
    message: str = Field(..., description="Diagnostic message string")
    stage_id: Optional[str] = Field(default=None, description="Target execution stage ID")
    rationale: Optional[str] = Field(default=None, description="Execution decision rationale")
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="UTC creation timestamp",
    )


class ExecutionPlannerDiagnostics:
    """
    Thread-safe diagnostics collector for ExecutionPlanner passes.
    """

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._items: List[ExecutionPlannerDiagnosticItem] = []

    def record_stage_creation(
        self,
        stage_id: str,
        stage_type: str,
        dependencies: Tuple[str, ...],
        rationale: str,
    ) -> None:
        """Records an execution stage creation trace."""
        item = ExecutionPlannerDiagnosticItem(
            stage="StageDecomposition",
            severity="INFO",
            message=f"Created ExecutionStage '{stage_id}' ({stage_type}) with dependencies {dependencies}",
            stage_id=stage_id,
            rationale=rationale,
        )
        with self._lock:
            self._items.append(item)

    def record_item(
        self,
        stage: str,
        message: str,
        severity: str = "INFO",
        stage_id: Optional[str] = None,
    ) -> None:
        """Records a general execution planner diagnostic trace."""
        item = ExecutionPlannerDiagnosticItem(
            stage=stage,
            severity=severity,
            message=message,
            stage_id=stage_id,
        )
        with self._lock:
            self._items.append(item)

    def get_items(self) -> Tuple[ExecutionPlannerDiagnosticItem, ...]:
        """Returns tuple of all logged diagnostic items."""
        with self._lock:
            return tuple(self._items)


__all__ = [
    "ExecutionPlannerDiagnosticItem",
    "ExecutionPlannerDiagnostics",
]
