"""
Unit test suite for LogicalPlanner end-to-end orchestration.
"""

import pytest

from graph_query_engine.logical import (
    LogicalPlan,
    LogicalPlanner,
    LogicalValidationError,
)
from graph_query_engine.planner import PlannerLifecycle, PlannerState
from graph_query_engine.query import PredicateBuilder, QueryBuilder


def test_logical_planner_end_to_end():
    query = (
        QueryBuilder(name="PlannerTestQuery")
        .with_lookup("sym_calc_1", name="calculate_metrics")
        .with_filter(PredicateBuilder.eq("status", "ACTIVE"))
        .with_projection("id", "name")
        .build()
    )

    lc = PlannerLifecycle()
    planner = LogicalPlanner()
    plan = planner.create_plan(query, lifecycle=lc)

    assert isinstance(plan, LogicalPlan)
    assert plan.query_id == query.query_id
    assert lc.current_state == PlannerState.COMPLETED
    assert plan.metadata.node_count >= 2
    assert plan.root_node.operator.operator_name == "LOGICAL_PROJECTION"
    assert len(plan.diagnostics) > 0
