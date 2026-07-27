# backend/graph_query_engine/tests/unit/optimizer/test_builder.py
"""Unit tests for builder pattern utilities."""

from graph_query_engine.optimizer import (
    PhysicalPlan,
    OptimizedPlanBuilder,
    OptimizationReportBuilder,
    RuleBuilder,
    FilterPushdownRule,
)


def test_optimized_plan_builder():
    builder = OptimizedPlanBuilder()
    plan = PhysicalPlan(operators=[{"type": "scan", "params": {}}])
    builder.from_physical(plan)
    builder.add_operator({"type": "filter", "params": {}})
    opt_plan = builder.build()
    assert len(opt_plan.operators) == 2


def test_rule_builder():
    base_rule = FilterPushdownRule()
    modified = RuleBuilder(base_rule).with_priority(99).with_enabled(False).build()
    assert modified.priority == 99
    assert modified.enabled is False
