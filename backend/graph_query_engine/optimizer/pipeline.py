# backend/graph_query_engine/optimizer/pipeline.py
"""OptimizationPipeline orchestrates phases and rule execution for physical plans.
It processes phases in topological dependency order and applies rules within each phase.
"""

from __future__ import annotations

from typing import List, Optional, Tuple, Dict, Any
from pydantic import BaseModel, Field

from .contracts import PhysicalPlan, OptimizedPhysicalPlan
from .context import OptimizationRuleContext
from .diagnostics import OptimizationDiagnostics, RejectedRuleInfo
from .metrics import OptimizationMetrics
from .phase import OptimizationPhase
from .registry import OptimizationRuleRegistry
from .rules import OptimizationRule
from datetime import datetime


class OptimizationPipeline:
    """Orchestrates execution of phases and optimization rules on a PhysicalPlan.

    Attributes:
        registry: The rule registry containing registered phases and rules.
        max_iterations: Maximum iteration passes over phases (for convergence).
    """

    def __init__(
        self,
        registry: Optional[OptimizationRuleRegistry] = None,
        max_iterations: int = 10,
    ) -> None:
        self._registry = registry or OptimizationRuleRegistry()
        self._max_iterations = max_iterations

    def run(
        self,
        plan: PhysicalPlan,
        statistics: Optional[Dict[str, Any]] = None,
        config: Optional[Dict[str, Any]] = None,
    ) -> Tuple[OptimizedPhysicalPlan, OptimizationDiagnostics, OptimizationMetrics]:
        """Runs all enabled phases and rules against the provided PhysicalPlan.

        Returns:
            A tuple of (OptimizedPhysicalPlan, OptimizationDiagnostics, OptimizationMetrics).
        """
        current_plan = plan
        diagnostics = OptimizationDiagnostics()
        metrics = OptimizationMetrics()

        phases = self._registry.ordered_phases()

        for phase in phases:
            if not phase.enabled:
                diagnostics.record_skipped(phase.name, reason="Phase disabled")
                continue

            sorted_rules = OptimizationRuleRegistry.order_rules(phase.rules)

            for rule in sorted_rules:
                if not rule.enabled:
                    diagnostics.record_skipped(rule.rule_id, reason="Rule disabled")
                    continue

                ctx = OptimizationRuleContext(
                    physical_plan=current_plan,
                    statistics=statistics,
                    config=config,
                    diagnostics=diagnostics,
                    metrics=metrics,
                )

                try:
                    if rule.can_apply(ctx):
                        result = rule.apply(ctx)
                        if result.changed:
                            current_plan = PhysicalPlan(operators=result.optimized_plan.operators)
                            if result.applied_info:
                                diagnostics.record_applied(result.applied_info.name, result.applied_info.details)
                            if result.metrics:
                                metrics = metrics.with_increment(
                                    operators_removed=result.metrics.operators_removed,
                                    operators_merged=result.metrics.operators_merged,
                                    depth_reduction=result.metrics.depth_reduction,
                                    pipeline_reduction=result.metrics.pipeline_reduction,
                                    join_improvements=result.metrics.join_improvements,
                                    projection_reductions=result.metrics.projection_reductions,
                                    filter_reductions=result.metrics.filter_reductions,
                                    estimated_complexity_reduction=result.metrics.estimated_complexity_reduction,
                                )
                        else:
                            if result.skipped_info:
                                diagnostics.record_skipped(result.skipped_info.name, result.skipped_info.reason)
                    else:
                        diagnostics.record_skipped(rule.rule_id, reason="can_apply returned False")
                except Exception as exc:
                    diagnostics.record_rejected(rule.rule_id, error=str(exc))

        final_optimized_plan = OptimizedPhysicalPlan(operators=current_plan.operators)
        return final_optimized_plan, diagnostics, metrics


class OptimizationPipelineBuilder:
    """Fluent builder for creating custom OptimizationPipeline instances."""

    def __init__(self) -> None:
        self._registry = OptimizationRuleRegistry()
        self._max_iterations = 10

    def with_registry(self, registry: OptimizationRuleRegistry) -> OptimizationPipelineBuilder:
        self._registry = registry
        return self

    def with_max_iterations(self, max_iterations: int) -> OptimizationPipelineBuilder:
        self._max_iterations = max_iterations
        return self

    def with_phase(self, phase: OptimizationPhase) -> OptimizationPipelineBuilder:
        self._registry.register_phase(phase)
        return self

    def with_rule(self, rule: OptimizationRule) -> OptimizationPipelineBuilder:
        self._registry.register_rule(rule)
        return self

    def build(self) -> OptimizationPipeline:
        return OptimizationPipeline(
            registry=self._registry,
            max_iterations=self._max_iterations,
        )


__all__ = ["OptimizationPipeline", "OptimizationPipelineBuilder"]
