"""
Cost Model Visitor Pattern.

Walks LogicalPlan nodes bottom-up to generate CostEstimate breakdowns.
"""

from typing import Any, Dict, List, Optional, Protocol, Tuple, runtime_checkable
from graph_query_engine.cost.estimate import CostEstimate, OperatorCostBreakdown
from graph_query_engine.cost.estimators import BaseOperatorCostEstimator
from graph_query_engine.cost.statistics import GraphStatisticsMetadata
from graph_query_engine.logical.plan import LogicalPlan, LogicalPlanNode


@runtime_checkable
class CostVisitor(Protocol):
    """Protocol for Cost Model Visitors."""

    def visit_plan(self, plan: LogicalPlan) -> Tuple[OperatorCostBreakdown, ...]:
        """Visits LogicalPlan and computes operator cost breakdowns."""
        ...

    def visit_plan_node(self, node: LogicalPlanNode) -> CostEstimate:
        """Visits a LogicalPlanNode and computes its CostEstimate."""
        ...


class BaseCostVisitor:
    """
    Bottom-up tree walker computing CostEstimate objects for LogicalPlanNode trees.
    """

    def __init__(self, stats: Optional[GraphStatisticsMetadata] = None) -> None:
        self.stats = stats
        self.breakdowns: List[OperatorCostBreakdown] = []

    def visit_plan(self, plan: LogicalPlan) -> Tuple[OperatorCostBreakdown, ...]:
        """Visits plan root and returns recorded breakdowns list."""
        self.breakdowns.clear()
        self.visit_plan_node(plan.root_node)
        return tuple(self.breakdowns)

    def visit_plan_node(self, node: LogicalPlanNode) -> CostEstimate:
        """Recursively visits child nodes first, then computes operator estimate."""
        child_estimates: List[CostEstimate] = []
        for child in node.children:
            child_estimates.append(self.visit_plan_node(child))

        child_tuple = tuple(child_estimates)
        estimate = BaseOperatorCostEstimator.estimate(node.operator, child_tuple, self.stats)

        breakdown = OperatorCostBreakdown(
            operator_id=node.operator.operator_id,
            operator_name=node.operator.operator_name,
            estimate=estimate,
        )
        self.breakdowns.append(breakdown)
        return estimate


__all__ = [
    "CostVisitor",
    "BaseCostVisitor",
]
