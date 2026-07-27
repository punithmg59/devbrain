# backend/graph_query_engine/tests/unit/optimizer/test_pipeline.py
"""Unit tests for OptimizationPipeline and topological phase ordering."""

from graph_query_engine.optimizer import (
    PhysicalPlan,
    PlannerOptimizer,
    OptimizationPipeline,
    OptimizationRuleRegistry,
    OptimizationPhase,
    ScanOptimizationRule,
    ConstantFoldingRule,
)


def test_pipeline_execution():
    registry = PlannerOptimizer.create_default_registry()
    pipeline = OptimizationPipeline(registry=registry)

    plan = PhysicalPlan(operators=[
        {"type": "scan", "params": {"index": "idx_name"}},
        {"type": "filter", "params": {"pred": "1 == 1"}},
    ])

    optimized_plan, diagnostics, metrics = pipeline.run(plan)

    assert optimized_plan.operators[0]["type"] == "index_scan"
    assert len(diagnostics.applied) > 0


def test_phase_ordering():
    registry = OptimizationRuleRegistry()
    registry.clear()

    p1 = OptimizationPhase(name="PhaseB", priority=20, dependencies=["PhaseA"], rules=[ConstantFoldingRule()])
    p2 = OptimizationPhase(name="PhaseA", priority=10, dependencies=[], rules=[ScanOptimizationRule()])

    registry.register_phase(p1)
    registry.register_phase(p2)

    ordered = registry.ordered_phases()
    assert len(ordered) == 2
    assert ordered[0].name == "PhaseA"
    assert ordered[1].name == "PhaseB"
