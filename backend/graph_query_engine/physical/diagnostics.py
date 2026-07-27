"""
Physical Planner Diagnostics Subsystem.

Collects audit logs, strategy choices, rejected alternatives, and cost rationales.
"""

from datetime import datetime, timezone
import threading
from typing import Any, Dict, List, Optional, Tuple
from pydantic import BaseModel, ConfigDict, Field


class PhysicalPlannerDiagnosticItem(BaseModel):
    """
    Immutable diagnostic item logged during physical plan generation.
    """
    model_config = ConfigDict(frozen=True)

    stage: str = Field(default="PhysicalPlanning", description="Planning stage identifier")
    severity: str = Field(default="INFO", description="Severity: INFO, WARNING, ERROR")
    message: str = Field(..., description="Diagnostic message string")
    operator_id: Optional[str] = Field(default=None, description="Target operator ID")
    selected_strategy: Optional[str] = Field(default=None, description="Selected execution strategy name")
    rejected_strategies: Tuple[str, ...] = Field(default_factory=tuple, description="Rejected strategy names")
    rationale: Optional[str] = Field(default=None, description="Strategy choice rationale string")
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="UTC creation timestamp",
    )


class PhysicalPlannerDiagnostics:
    """
    Thread-safe diagnostics collector for PhysicalPlanner passes.
    """

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._items: List[PhysicalPlannerDiagnosticItem] = []

    def record_choice(
        self,
        operator_id: str,
        selected_strategy: str,
        rejected_strategies: Tuple[str, ...],
        rationale: str,
    ) -> None:
        """Records a physical strategy selection choice with rationale."""
        item = PhysicalPlannerDiagnosticItem(
            stage="StrategySelection",
            severity="INFO",
            message=f"Operator '{operator_id}': Selected '{selected_strategy}' over {rejected_strategies}",
            operator_id=operator_id,
            selected_strategy=selected_strategy,
            rejected_strategies=rejected_strategies,
            rationale=rationale,
        )
        with self._lock:
            self._items.append(item)

    def record_item(
        self,
        stage: str,
        message: str,
        severity: str = "INFO",
        operator_id: Optional[str] = None,
    ) -> None:
        """Records a general physical planner diagnostic trace."""
        item = PhysicalPlannerDiagnosticItem(
            stage=stage,
            severity=severity,
            message=message,
            operator_id=operator_id,
        )
        with self._lock:
            self._items.append(item)

    def get_items(self) -> Tuple[PhysicalPlannerDiagnosticItem, ...]:
        """Returns tuple of all logged diagnostic items."""
        with self._lock:
            return tuple(self._items)


__all__ = [
    "PhysicalPlannerDiagnosticItem",
    "PhysicalPlannerDiagnostics",
]
