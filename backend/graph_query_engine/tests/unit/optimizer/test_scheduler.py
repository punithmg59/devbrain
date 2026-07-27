# backend/graph_query_engine/tests/unit/optimizer/test_scheduler.py
"""Unit tests for OptimizationScheduler fixed-point convergence."""

from graph_query_engine.optimizer import (
    PhysicalPlan,
    PlannerOptimizer,
    OptimizationScheduler,
    OptimizationPipeline,
)


def test_scheduler_fixed_point_convergence():
    registry = PlannerOptimizer.create_default_registry()
    pipeline = OptimizationPipeline(registry=registry)
    scheduler = OptimizationScheduler(pipeline=pipeline, max_iterations=5)

    plan = PhysicalPlan(operators=[
        {"type": "scan", "params": {"index": "idx_name"}},
        {"type": "filter", "params": {"pred": "1 == 1"}},
        {"type": "filter", "params": {"pred": "true"}},
    ])

    optimized_plan, diagnostics, metrics, iterations = scheduler.execute(plan)

    assert iterations <= 5
    assert len(optimized_plan.operators) == 1
    assert optimized_plan.operators[0]["type"] == "index_scan"
