"""
Unit test suite for CostEstimator end-to-end orchestration.
"""

from graph_query_engine.cost import CostEstimator, CostReport
from graph_query_engine.logical import LogicalPlanBuilder
from graph_query_engine.query import PredicateBuilder


def test_cost_estimator_end_to_end():
    plan = (
        LogicalPlanBuilder()
        .with_lookup("sym_test_1", name="calculate_total")
        .with_filter(PredicateBuilder.eq("status", "ACTIVE"))
        .with_projection("id", "name")
        .with_limit(10)
        .build()
    )

    estimator = CostEstimator()
    report = estimator.estimate_plan_cost(plan)

    assert isinstance(report, CostReport)
    assert report.plan_id == plan.plan_id
    assert report.total_cost_estimate.estimated_total_cost > 0.0
    assert len(report.operator_costs) == 4
    assert report.total_cost_estimate.confidence_score > 0.0
