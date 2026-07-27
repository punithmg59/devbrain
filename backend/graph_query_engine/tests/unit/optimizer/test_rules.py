# backend/graph_query_engine/tests/unit/optimizer/test_rules.py
"""Unit tests for all 13 concrete optimization rules."""

from graph_query_engine.optimizer import (
    PhysicalPlan,
    OptimizationRuleContext,
    FilterPushdownRule,
    ProjectionPushdownRule,
    OperatorFusionRule,
    RedundantFilterEliminationRule,
    RedundantProjectionEliminationRule,
    ConstantFoldingRule,
    DeadCodeEliminationRule,
    JoinReorderingRule,
    ExpandOptimizationRule,
    SubqueryUnrollingRule,
    LimitPushdownRule,
    ScanOptimizationRule,
    IndexScanSelectionRule,
)


def test_filter_pushdown_rule():
    rule = FilterPushdownRule()
    plan = PhysicalPlan(operators=[
        {"type": "expand", "params": {"index_key": "rel_type"}},
        {"type": "filter", "params": {"pred": "age > 30"}},
    ])
    ctx = OptimizationRuleContext(physical_plan=plan)
    assert rule.can_apply(ctx) is True

    result = rule.apply(ctx)
    assert result.changed is True
    assert result.optimized_plan.operators[0]["type"] == "filter"
    assert result.optimized_plan.operators[1]["type"] == "expand"


def test_projection_pushdown_rule():
    rule = ProjectionPushdownRule()
    plan = PhysicalPlan(operators=[
        {"type": "sort", "params": {"key": "name"}},
        {"type": "projection", "params": {"fields": ["name"]}},
    ])
    ctx = OptimizationRuleContext(physical_plan=plan)
    assert rule.can_apply(ctx) is True

    result = rule.apply(ctx)
    assert result.changed is True
    assert result.optimized_plan.operators[0]["type"] == "projection"
    assert result.optimized_plan.operators[1]["type"] == "sort"


def test_operator_fusion_rule():
    rule = OperatorFusionRule()
    plan = PhysicalPlan(operators=[
        {"type": "filter", "params": {"pred": "a > 1"}},
        {"type": "filter", "params": {"pred": "b < 10"}},
    ])
    ctx = OptimizationRuleContext(physical_plan=plan)
    assert rule.can_apply(ctx) is True

    result = rule.apply(ctx)
    assert result.changed is True
    assert len(result.optimized_plan.operators) == 1
    assert result.optimized_plan.operators[0]["type"] == "filter"
    assert result.optimized_plan.operators[0]["params"]["pred"] == "(a > 1) AND (b < 10)"


def test_redundant_filter_elimination_rule():
    rule = RedundantFilterEliminationRule()
    plan = PhysicalPlan(operators=[
        {"type": "filter", "params": {"pred": "true"}},
        {"type": "scan", "params": {}},
    ])
    ctx = OptimizationRuleContext(physical_plan=plan)
    assert rule.can_apply(ctx) is True

    result = rule.apply(ctx)
    assert result.changed is True
    assert len(result.optimized_plan.operators) == 1
    assert result.optimized_plan.operators[0]["type"] == "scan"


def test_redundant_projection_elimination_rule():
    rule = RedundantProjectionEliminationRule()
    plan = PhysicalPlan(operators=[
        {"type": "scan", "params": {}},
        {"type": "projection", "params": {"fields": ["*"]}},
    ])
    ctx = OptimizationRuleContext(physical_plan=plan)
    assert rule.can_apply(ctx) is True

    result = rule.apply(ctx)
    assert result.changed is True
    assert len(result.optimized_plan.operators) == 1
    assert result.optimized_plan.operators[0]["type"] == "scan"


def test_constant_folding_rule():
    rule = ConstantFoldingRule()
    plan = PhysicalPlan(operators=[
        {"type": "filter", "params": {"pred": "status == 'active' and 1 == 1"}},
    ])
    ctx = OptimizationRuleContext(physical_plan=plan)
    assert rule.can_apply(ctx) is True

    result = rule.apply(ctx)
    assert result.changed is True
    assert "true" in result.optimized_plan.operators[0]["params"]["pred"]


def test_dead_code_elimination_rule():
    rule = DeadCodeEliminationRule()
    plan = PhysicalPlan(operators=[
        {"type": "filter", "params": {"pred": "false"}},
        {"type": "expand", "params": {}},
        {"type": "projection", "params": {}},
    ])
    ctx = OptimizationRuleContext(physical_plan=plan)
    assert rule.can_apply(ctx) is True

    result = rule.apply(ctx)
    assert result.changed is True
    assert len(result.optimized_plan.operators) == 1
    assert result.optimized_plan.operators[0]["type"] == "filter"


def test_join_reordering_rule():
    rule = JoinReorderingRule()
    plan = PhysicalPlan(operators=[{"type": "join", "params": {}}])
    ctx = OptimizationRuleContext(physical_plan=plan)
    assert rule.can_apply(ctx) is False


def test_expand_optimization_rule():
    rule = ExpandOptimizationRule()
    plan = PhysicalPlan(operators=[
        {"type": "expand", "params": {"index_key": "KNOWS"}},
    ])
    ctx = OptimizationRuleContext(physical_plan=plan)
    assert rule.can_apply(ctx) is True

    result = rule.apply(ctx)
    assert result.changed is True
    assert result.optimized_plan.operators[0]["type"] == "indexed_expand"


def test_subquery_unrolling_rule():
    rule = SubqueryUnrollingRule()
    plan = PhysicalPlan(operators=[
        {"type": "subquery", "params": {"subplan": [{"type": "scan", "params": {}}]}},
    ])
    ctx = OptimizationRuleContext(physical_plan=plan)
    assert rule.can_apply(ctx) is True

    result = rule.apply(ctx)
    assert result.changed is True
    assert result.optimized_plan.operators[0]["type"] == "scan"


def test_limit_pushdown_rule():
    rule = LimitPushdownRule()
    plan = PhysicalPlan(operators=[
        {"type": "projection", "params": {"fields": ["id"]}},
        {"type": "limit", "params": {"count": 10}},
    ])
    ctx = OptimizationRuleContext(physical_plan=plan)
    assert rule.can_apply(ctx) is True

    result = rule.apply(ctx)
    assert result.changed is True
    assert result.optimized_plan.operators[0]["type"] == "limit"
    assert result.optimized_plan.operators[1]["type"] == "projection"


def test_scan_optimization_rule():
    rule = ScanOptimizationRule()
    plan = PhysicalPlan(operators=[
        {"type": "scan", "params": {"index": "idx_user_id"}},
    ])
    ctx = OptimizationRuleContext(physical_plan=plan)
    assert rule.can_apply(ctx) is True

    result = rule.apply(ctx)
    assert result.changed is True
    assert result.optimized_plan.operators[0]["type"] == "index_scan"


def test_index_scan_selection_rule():
    rule = IndexScanSelectionRule()
    plan = PhysicalPlan(operators=[
        {"type": "index_scan", "params": {"composite_keys": ["tenant_id", "user_id"]}},
    ])
    ctx = OptimizationRuleContext(physical_plan=plan)
    assert rule.can_apply(ctx) is True

    result = rule.apply(ctx)
    assert result.changed is True
    assert result.optimized_plan.operators[0]["type"] == "composite_index_scan"
