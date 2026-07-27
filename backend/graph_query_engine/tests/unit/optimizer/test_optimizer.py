# backend/graph_query_engine/tests/unit/optimizer/test_optimizer.py
"""End-to-end integration test for PlannerOptimizer."""

from graph_query_engine.optimizer import (
    PhysicalPlan,
    PlannerOptimizer,
    OptimizedPhysicalPlan,
    OptimizationReport,
)


def test_planner_optimizer_end_to_end():
    optimizer = PlannerOptimizer()

    initial_plan = PhysicalPlan(operators=[
        {"type": "scan", "params": {"index": "user_idx"}},
        {"type": "filter", "params": {"pred": "1 == 1"}},
        {"type": "filter", "params": {"pred": "age > 21"}},
        {"type": "projection", "params": {"fields": ["*"]}},
    ])

    optimized_plan, report = optimizer.optimize_with_report(initial_plan)

    assert isinstance(optimized_plan, OptimizedPhysicalPlan)
    assert isinstance(report, OptimizationReport)
    assert len(report.applied_rules) > 0
    assert report.metrics.operators_removed > 0 or report.metrics.filter_reductions > 0
