# backend/graph_query_engine/optimizer/scheduler.py
"""Scheduler for fixed-point optimization passes.
Drives the OptimizationPipeline repeatedly until convergence (no rules modify the plan)
or maximum iteration limit is reached.
"""

from __future__ import annotations

from typing import Any, Dict, Optional, Tuple

from .contracts import PhysicalPlan, OptimizedPhysicalPlan
from .diagnostics import OptimizationDiagnostics
from .metrics import OptimizationMetrics
from .pipeline import OptimizationPipeline


class OptimizationScheduler:
    """Fixed-point optimization scheduler.

    Repeatedly runs the optimization pipeline until convergence (plan state remains identical across an iteration)
    or until max_iterations limit is reached.
    """

    def __init__(
        self,
        pipeline: Optional[OptimizationPipeline] = None,
        max_iterations: int = 10,
    ) -> None:
        self._pipeline = pipeline or OptimizationPipeline()
        self._max_iterations = max_iterations

    def execute(
        self,
        plan: PhysicalPlan,
        statistics: Optional[Dict[str, Any]] = None,
        config: Optional[Dict[str, Any]] = None,
    ) -> Tuple[OptimizedPhysicalPlan, OptimizationDiagnostics, OptimizationMetrics, int]:
        """Executes passes until convergence or max_iterations limit is reached.

        Returns:
            Tuple of (OptimizedPhysicalPlan, OptimizationDiagnostics, OptimizationMetrics, total_iterations).
        """
        current_plan = plan
        aggregated_diagnostics = OptimizationDiagnostics()
        aggregated_metrics = OptimizationMetrics()

        iteration = 0
        while iteration < self._max_iterations:
            iteration += 1
            optimized_plan, diagnostics, metrics = self._pipeline.run(
                current_plan,
                statistics=statistics,
                config=config,
            )

            # Record diagnostics and accumulate metrics
            for item in diagnostics.applied:
                aggregated_diagnostics.record_applied(item.name, item.details)
            for item in diagnostics.skipped:
                aggregated_diagnostics.record_skipped(item.name, item.reason)
            for item in diagnostics.rejected:
                aggregated_diagnostics.record_rejected(item.name, item.error)

            aggregated_metrics = aggregated_metrics.with_increment(
                operators_removed=metrics.operators_removed,
                operators_merged=metrics.operators_merged,
                depth_reduction=metrics.depth_reduction,
                pipeline_reduction=metrics.pipeline_reduction,
                join_improvements=metrics.join_improvements,
                projection_reductions=metrics.projection_reductions,
                filter_reductions=metrics.filter_reductions,
                estimated_complexity_reduction=metrics.estimated_complexity_reduction,
            )

            # Check convergence
            if optimized_plan.operators == current_plan.operators:
                # Plan reached fixed point (no change in operators)
                break

            current_plan = PhysicalPlan(operators=optimized_plan.operators)

        final_plan = OptimizedPhysicalPlan(operators=current_plan.operators)
        return final_plan, aggregated_diagnostics, aggregated_metrics, iteration


__all__ = ["OptimizationScheduler"]
