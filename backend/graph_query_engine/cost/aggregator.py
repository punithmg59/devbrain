"""
Cost Aggregator Subsystem.

Aggregates per-operator cost estimates into total plan cost and cumulative resource metrics.
"""

from typing import List, Tuple
from graph_query_engine.cost.estimate import CostEstimate, OperatorCostBreakdown


class CostAggregator:
    """
    Aggregates per-operator cost estimates into total plan CostEstimate.
    """

    @classmethod
    def aggregate_plan_cost(
        cls,
        breakdowns: Tuple[OperatorCostBreakdown, ...],
    ) -> CostEstimate:
        """
        Computes cumulative plan CostEstimate from per-operator breakdowns.
        """
        if not breakdowns:
            return CostEstimate()

        root_breakdown = breakdowns[-1]
        root_estimate = root_breakdown.estimate

        total_cpu = sum(b.estimate.cpu_cost for b in breakdowns)
        total_mem = max((b.estimate.memory_cost for b in breakdowns), default=0.0)
        total_trav = sum(b.estimate.traversal_cost for b in breakdowns)
        avg_confidence = sum(b.estimate.confidence_score for b in breakdowns) / float(len(breakdowns))

        total_operator_cost = sum(b.estimate.estimated_operator_cost for b in breakdowns)

        return CostEstimate(
            cpu_cost=total_cpu,
            memory_cost=total_mem,
            traversal_cost=total_trav,
            estimated_cardinality=root_estimate.estimated_cardinality,
            estimated_selectivity=root_estimate.estimated_selectivity,
            estimated_result_size_bytes=root_estimate.estimated_result_size_bytes,
            estimated_depth=root_estimate.estimated_depth,
            estimated_fan_out=root_estimate.estimated_fan_out,
            estimated_fan_in=root_estimate.estimated_fan_in,
            estimated_operator_cost=root_estimate.estimated_operator_cost,
            estimated_total_cost=total_operator_cost,
            confidence_score=avg_confidence,
        )


__all__ = ["CostAggregator"]
