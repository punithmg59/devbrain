# backend/graph_query_engine/optimizer/metrics.py
"""Metrics tracking for the Planner Optimizer.
All metrics are simple counters aggregated during the optimization run.
"""

from dataclasses import dataclass, field

@dataclass(frozen=True)
class OptimizationMetrics:
    """Immutable counters representing optimization impact.
    All fields default to zero and are updated by creating a new instance
    (builder pattern) to preserve immutability.
    """

    operators_removed: int = 0
    operators_merged: int = 0
    depth_reduction: int = 0
    pipeline_reduction: int = 0
    join_improvements: int = 0
    projection_reductions: int = 0
    filter_reductions: int = 0
    estimated_complexity_reduction: float = 0.0

    def with_increment(self, **kwargs) -> "OptimizationMetrics":
        """Return a new ``OptimizationMetrics`` with the provided increments applied.
        Example: ``metrics = metrics.with_increment(operators_removed=1)``.
        """
        return OptimizationMetrics(
            operators_removed=self.operators_removed + kwargs.get("operators_removed", 0),
            operators_merged=self.operators_merged + kwargs.get("operators_merged", 0),
            depth_reduction=self.depth_reduction + kwargs.get("depth_reduction", 0),
            pipeline_reduction=self.pipeline_reduction + kwargs.get("pipeline_reduction", 0),
            join_improvements=self.join_improvements + kwargs.get("join_improvements", 0),
            projection_reductions=self.projection_reductions + kwargs.get("projection_reductions", 0),
            filter_reductions=self.filter_reductions + kwargs.get("filter_reductions", 0),
            estimated_complexity_reduction=self.estimated_complexity_reduction + kwargs.get("estimated_complexity_reduction", 0.0),
        )

__all__ = ["OptimizationMetrics"]
