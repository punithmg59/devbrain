# backend/graph_query_engine/optimizer/builder.py
"""Builders for the Planner Optimizer outputs and configurations.
These utilities construct immutable models for the optimized plan, reports,
pipeline configurations, and rules while preserving frozen guarantees.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Type

from pydantic import BaseModel

from .contracts import PhysicalPlan, OptimizedPhysicalPlan
from .diagnostics import AppliedRuleInfo, SkippedRuleInfo, RejectedRuleInfo
from .metrics import OptimizationMetrics
from .report import OptimizationReport
from .rules import OptimizationRule


class OptimizedPlanBuilder:
    """Fluent builder for :class:`OptimizedPhysicalPlan`.

    Receives a list of operator dictionaries (or a ``PhysicalPlan``) and produces a frozen model.
    """

    def __init__(self) -> None:
        self._operators: List[dict] = []

    def from_physical(self, plan: PhysicalPlan) -> OptimizedPlanBuilder:
        self._operators = [dict(op) for op in plan.operators]
        return self

    def with_operators(self, ops: List[dict]) -> OptimizedPlanBuilder:
        self._operators = [dict(op) for op in ops]
        return self

    def add_operator(self, op: dict) -> OptimizedPlanBuilder:
        self._operators.append(dict(op))
        return self

    def build(self) -> OptimizedPhysicalPlan:
        return OptimizedPhysicalPlan(operators=self._operators)


class OptimizationReportBuilder:
    """Builder for :class:`OptimizationReport`.

    Collects before/after plans, rule diagnostics, and metrics into an immutable report object.
    """

    def __init__(self) -> None:
        self._before: Optional[PhysicalPlan] = None
        self._after: Optional[OptimizedPhysicalPlan] = None
        self._applied: List[AppliedRuleInfo] = []
        self._skipped: List[SkippedRuleInfo] = []
        self._rejected: List[RejectedRuleInfo] = []
        self._metrics: OptimizationMetrics = OptimizationMetrics()

    def before(self, plan: PhysicalPlan) -> OptimizationReportBuilder:
        self._before = plan
        return self

    def after(self, plan: OptimizedPhysicalPlan) -> OptimizationReportBuilder:
        self._after = plan
        return self

    def applied_rules(self, applied: List[AppliedRuleInfo]) -> OptimizationReportBuilder:
        self._applied = list(applied)
        return self

    def skipped_rules(self, skipped: List[SkippedRuleInfo]) -> OptimizationReportBuilder:
        self._skipped = list(skipped)
        return self

    def rejected_rules(self, rejected: List[RejectedRuleInfo]) -> OptimizationReportBuilder:
        self._rejected = list(rejected)
        return self

    def metrics(self, metrics: OptimizationMetrics) -> OptimizationReportBuilder:
        self._metrics = metrics
        return self

    def build(self) -> OptimizationReport:
        if self._before is None or self._after is None:
            raise ValueError("Both before and after plans must be set before building a report")
        return OptimizationReport(
            before_plan=self._before,
            after_plan=self._after,
            applied_rules=self._applied,
            skipped_rules=self._skipped,
            rejected_rules=self._rejected,
            metrics=self._metrics,
        )


class RuleBuilder:
    """Fluent builder for creating custom or modified OptimizationRule configurations."""

    def __init__(self, rule: OptimizationRule) -> None:
        self._rule = rule
        self._overrides: Dict[str, Any] = {}

    def with_priority(self, priority: int) -> RuleBuilder:
        self._overrides["priority"] = priority
        return self

    def with_enabled(self, enabled: bool) -> RuleBuilder:
        self._overrides["enabled"] = enabled
        return self

    def build(self) -> OptimizationRule:
        if not self._overrides:
            return self._rule
        return self._rule.model_copy(update=self._overrides)


__all__ = [
    "OptimizedPlanBuilder",
    "OptimizationReportBuilder",
    "RuleBuilder",
]
