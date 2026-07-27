"""
Cardinality Estimator Engine.

Computes expected output entity counts, branching factors, fan-out/fan-in degrees.
"""

from typing import Optional
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


class CardinalityEstimator:
    """
    Pure functional estimator computing expected output entity cardinality and fan-out/fan-in.
    """

    @classmethod
    def estimate_operator_cardinality(
        cls,
        operator: LogicalOperator,
        child_cardinalities: tuple[float, ...],
        stats: Optional[GraphStatisticsMetadata] = None,
    ) -> float:
        """
        Calculates expected output cardinality for an operator given child input cardinalities.
        """
        input_card = child_cardinalities[0] if child_cardinalities else 1.0

        if isinstance(operator, LogicalLookupOperator):
            return 1.0

        elif isinstance(operator, LogicalExpandOperator):
            req = operator.traversal_request
            avg_deg = stats.edges.average_degree if stats else 5.0
            max_depth = req.constraints.max_depth if req else 1
            # Expansion factor = avg_deg ^ max_depth
            expansion_factor = (avg_deg ** min(max_depth, 3))
            return max(input_card * expansion_factor, 1.0)

        elif isinstance(operator, LogicalFilterOperator):
            sel = SelectivityEstimator.estimate_predicate_selectivity(operator.predicate, stats)
            return max(input_card * sel, 0.0)

        elif isinstance(operator, LogicalProjectionOperator):
            return input_card

        elif isinstance(operator, LogicalAggregateOperator):
            return 1.0

        elif isinstance(operator, LogicalGroupingOperator):
            # Grouping cardinality ~ min(input_card, 20)
            return min(input_card, 20.0)

        elif isinstance(operator, LogicalSortingOperator):
            return input_card

        elif isinstance(operator, LogicalDeduplicationOperator):
            return max(input_card * 0.8, 1.0)

        elif isinstance(operator, LogicalLimitOperator):
            return min(input_card, float(operator.limit))

        elif isinstance(operator, LogicalJoinOperator):
            left_c = child_cardinalities[0] if len(child_cardinalities) > 0 else 1.0
            right_c = child_cardinalities[1] if len(child_cardinalities) > 1 else 1.0
            sel = SelectivityEstimator.estimate_predicate_selectivity(operator.on_predicate, stats)
            return max(left_c * right_c * sel, 1.0)

        return input_card


__all__ = ["CardinalityEstimator"]
