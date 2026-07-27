"""
Unit test suite for LogicalPlanValidator structural validation.
"""

from graph_query_engine.logical import (
    LogicalJoinOperator,
    LogicalOperatorBuilder,
    LogicalPlan,
    LogicalPlanBuilder,
    LogicalPlanNode,
    LogicalPlanValidator,
)
from graph_query_engine.query import PredicateBuilder


def test_logical_plan_validator_clean_pass():
    plan = LogicalPlanBuilder().with_lookup("sym_1").with_projection("id").build()
    report = LogicalPlanValidator.validate(plan)

    assert report.is_valid is True
    assert len(report.violations) == 0


def test_logical_plan_validator_join_children_violation():
    join_op = LogicalJoinOperator(
        operator_id="op_join_invalid",
        on_predicate=PredicateBuilder.eq("id", "id"),
    )
    # Join with only 1 child input (invalid)
    child_node = LogicalPlanNode(
        node_id="child_1",
        operator=LogicalOperatorBuilder.lookup("sym_1"),
    )
    invalid_root = LogicalPlanNode(
        node_id="root_join",
        operator=join_op,
        children=(child_node,),
    )

    plan = LogicalPlanBuilder().build()
    invalid_plan = LogicalPlan.model_construct(
        plan_id=plan.plan_id,
        query_id=plan.query_id,
        version=plan.version,
        metadata=plan.metadata,
        statistics=plan.statistics,
        root_node=invalid_root,
        diagnostics=plan.diagnostics,
    )

    report = LogicalPlanValidator.validate(invalid_plan)
    assert report.is_valid is False
    assert any(v.rule_id == "LVAL_004_JOIN_CHILDREN" for v in report.violations)
