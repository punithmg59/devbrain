"""
Unit test suite for ExecutionPlanner end-to-end orchestration.
"""

from graph_query_engine.cost import CostEstimator
from graph_query_engine.execution import ExecutionPlan, ExecutionPlanner
from graph_query_engine.logical import LogicalPlanBuilder
from graph_query_engine.physical import PhysicalPlanner
from graph_query_engine.query import PredicateBuilder


def test_execution_planner_end_to_end():
    logical_plan = (
        LogicalPlanBuilder()
        .with_lookup("sym_exec_1", name="compute_graph")
        .with_filter(PredicateBuilder.eq("status", "ACTIVE"))
        .with_projection("id", "name")
        .with_limit(10)
        .build()
    )

    cost_report = CostEstimator().estimate_plan_cost(logical_plan)
    phys_plan = PhysicalPlanner().create_physical_plan(logical_plan, cost_report)

    eplanner = ExecutionPlanner()
    eplan = eplanner.create_execution_plan(phys_plan)

    assert isinstance(eplan, ExecutionPlan)
    assert eplan.physical_plan_id == phys_plan.plan_id
    assert eplan.query_id == phys_plan.query_id
    assert len(eplan.stages) >= 3
    assert eplan.dependency_graph.is_acyclic() is True
    assert len(eplan.pipeline.stages) == len(eplan.stages)
