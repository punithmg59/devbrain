# backend/graph_query_engine/optimizer/report.py
"""OptimizationReport aggregates before/after plans, diagnostics, and metrics.
It is an immutable Pydantic model for easy serialization.
"""

from __future__ import annotations

from datetime import datetime
from typing import List

from pydantic import BaseModel, Field, ConfigDict

from .contracts import PhysicalPlan, OptimizedPhysicalPlan
from .diagnostics import AppliedRuleInfo, SkippedRuleInfo, RejectedRuleInfo
from .metrics import OptimizationMetrics


class OptimizationReport(BaseModel):
    """Report generated after an optimization run."""

    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    timestamp: datetime = Field(default_factory=datetime.utcnow)
    before_plan: PhysicalPlan
    after_plan: OptimizedPhysicalPlan
    applied_rules: List[AppliedRuleInfo] = Field(default_factory=list)
    skipped_rules: List[SkippedRuleInfo] = Field(default_factory=list)
    rejected_rules: List[RejectedRuleInfo] = Field(default_factory=list)
    metrics: OptimizationMetrics = Field(default_factory=OptimizationMetrics)


__all__ = ["OptimizationReport"]
