# backend/graph_query_engine/optimizer/context.py
"""Immutable context passed to each optimization rule.
It aggregates all information a rule may need without allowing mutation.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from pydantic import BaseModel, Field, ConfigDict

from .contracts import PhysicalPlan
from .diagnostics import OptimizationDiagnostics
from .metrics import OptimizationMetrics


class OptimizationRuleContext(BaseModel):
    """Immutable container with data accessible to optimization rules."""

    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    physical_plan: PhysicalPlan = Field(...)
    cost_report: Optional[Any] = None
    statistics: Optional[Dict[str, Any]] = None
    config: Optional[Dict[str, Any]] = None
    diagnostics: OptimizationDiagnostics = Field(default_factory=OptimizationDiagnostics)
    metrics: OptimizationMetrics = Field(default_factory=OptimizationMetrics)


__all__ = ["OptimizationRuleContext"]
