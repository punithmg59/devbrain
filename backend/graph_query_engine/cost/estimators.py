"""
Operator-Specific Cost Estimators.

Computes a CostEstimate for individual LogicalOperator nodes.
"""

from typing import Optional, Tuple
from graph_query_engine.cost.cardinality import CardinalityEstimator
from graph_query_engine.cost.estimate import CostEstimate
from graph_query_engine.cost.resources import ResourceEstimator
from graph_query_engine.cost.selectivity import SelectivityEstimator
from graph_query_engine.cost.statistics import GraphStatisticsMetadata
from graph_query_engine.logical.operators import (
    LogicalAggregateOperator,
    LogicalDeduplicationOperator,
    LogicalExpandOperator,
    LogicalFilterOperator,
    LogicalGroupingOperator,
    LogicalJoinOperator,
    LogicalLimitOperator,
    LogicalLookupOperator,
    LogicalOperator,
    LogicalProjectionOperator,
    LogicalSortingOperator,
)


class BaseOperatorCostEstimator:
    """Base class for operator cost estimation rules."""

    @classmethod
    def estimate(
        cls,
        operator: LogicalOperator,
        child_estimates: Tuple[CostEstimate, ...],
        stats: Optional[GraphStatisticsMetadata] = None,
    ) -> CostEstimate:
        """Computes CostEstimate for the given operator and child estimates."""
        child_cardinalities = tuple(c.estimated_cardinality for c in child_estimates)
        child_total_cost = sum(c.estimated_total_cost for c in child_estimates)

        cardinality = CardinalityEstimator.estimate_operator_cardinality(operator, child_cardinalities, stats)
        resources = ResourceEstimator.estimate_operator_resources(
            operator.operator_name, cardinality, len(operator.output_schema)
        )

        selectivity = 1.0
        if isinstance(operator, LogicalFilterOperator):
            selectivity = SelectivityEstimator.estimate_predicate_selectivity(operator.predicate, stats)

        traversal_cost = 0.0
        if isinstance(operator, LogicalExpandOperator):
            avg_deg = stats.edges.average_degree if stats else 5.0
            traversal_cost = cardinality * avg_deg * 2.0

        op_self_cost = resources.cpu_cycles + (resources.memory_bytes / 1024.0) + traversal_cost
        total_cost = child_total_cost + op_self_cost

        return CostEstimate(
            cpu_cost=resources.cpu_cycles,
            memory_cost=resources.memory_bytes,
            traversal_cost=traversal_cost,
            estimated_cardinality=cardinality,
            estimated_selectivity=selectivity,
            estimated_result_size_bytes=resources.payload_size_bytes,
            estimated_depth=1.0 + (max((c.estimated_depth for c in child_estimates), default=0.0)),
            estimated_fan_out=stats.edges.average_degree if stats else 5.0,
            estimated_fan_in=stats.edges.average_degree if stats else 5.0,
            estimated_operator_cost=op_self_cost,
            estimated_total_cost=total_cost,
            confidence_score=0.95 if stats else 0.80,
        )


class LookupCostEstimator(BaseOperatorCostEstimator):
    """Estimates cost for LogicalLookupOperator."""
    pass


class ExpandCostEstimator(BaseOperatorCostEstimator):
    """Estimates cost for LogicalExpandOperator."""
    pass


class FilterCostEstimator(BaseOperatorCostEstimator):
    """Estimates cost for LogicalFilterOperator."""
    pass


class ProjectionCostEstimator(BaseOperatorCostEstimator):
    """Estimates cost for LogicalProjectionOperator."""
    pass


class AggregateCostEstimator(BaseOperatorCostEstimator):
    """Estimates cost for LogicalAggregateOperator."""
    pass


class GroupingCostEstimator(BaseOperatorCostEstimator):
    """Estimates cost for LogicalGroupingOperator."""
    pass


class SortingCostEstimator(BaseOperatorCostEstimator):
    """Estimates cost for LogicalSortingOperator."""
    pass


class DeduplicationCostEstimator(BaseOperatorCostEstimator):
    """Estimates cost for LogicalDeduplicationOperator."""
    pass


class JoinCostEstimator(BaseOperatorCostEstimator):
    """Estimates cost for LogicalJoinOperator."""
    pass


class LimitCostEstimator(BaseOperatorCostEstimator):
    """Estimates cost for LogicalLimitOperator."""
    pass


__all__ = [
    "BaseOperatorCostEstimator",
    "LookupCostEstimator",
    "ExpandCostEstimator",
    "FilterCostEstimator",
    "ProjectionCostEstimator",
    "AggregateCostEstimator",
    "GroupingCostEstimator",
    "SortingCostEstimator",
    "DeduplicationCostEstimator",
    "JoinCostEstimator",
    "LimitCostEstimator",
]
