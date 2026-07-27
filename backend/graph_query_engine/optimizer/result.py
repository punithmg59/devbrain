# backend/graph_query_engine/optimizer/result.py
"""Result object returned by an OptimizationRule.
Encapsulates the transformed plan, a flag indicating whether the plan changed,
summary text, and optional diagnostics/metrics.
"""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field, ConfigDict

from .contracts import OptimizedPhysicalPlan
from .diagnostics import AppliedRuleInfo, SkippedRuleInfo, RejectedRuleInfo
from .metrics import OptimizationMetrics


class OptimizationRuleResult(BaseModel):
    """Immutable result of applying a single optimization rule."""

    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    optimized_plan: OptimizedPhysicalPlan = Field(...)
    changed: bool = Field(...)
    summary: str = Field(...)
    applied_info: Optional[AppliedRuleInfo] = None
    skipped_info: Optional[SkippedRuleInfo] = None
    rejected_info: Optional[RejectedRuleInfo] = None
    metrics: Optional[OptimizationMetrics] = None


__all__ = ["OptimizationRuleResult"]
