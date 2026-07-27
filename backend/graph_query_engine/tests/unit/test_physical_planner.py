"""
Unit test suite for PhysicalPlanner end-to-end orchestration.
"""

from graph_query_engine.cost import CostEstimator
from graph_query_engine.logical import LogicalPlanBuilder
from graph_query_engine.physical import PhysicalPlan, PhysicalPlanner
from graph_query_engine.query import PredicateBuilder


def test_physical_planner_end_to_end():
    logical_plan = (
        LogicalPlanBuilder()
        .with_lookup("sym_main_fn", name="main")
        .with_filter(PredicateBuilder.eq("status", "ACTIVE"))
        .with_projection("id", "name")
        .with_limit(5)
        .build()
    )

    cost_estimator = CostEstimator()
    cost_report = cost_estimator.estimate_plan_cost(logical_plan)

    planner = PhysicalPlanner()
    phys_plan = planner.create_physical_plan(logical_plan, cost_report)

    assert isinstance(phys_plan, PhysicalPlan)
    assert phys_plan.logical_plan_id == logical_plan.plan_id
    assert phys_plan.query_id == logical_plan.query_id
    assert phys_plan.metadata.node_count >= 3
    assert len(phys_plan.diagnostics) > 0
