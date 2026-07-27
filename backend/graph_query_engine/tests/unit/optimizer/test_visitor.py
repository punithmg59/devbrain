# backend/graph_query_engine/tests/unit/optimizer/test_visitor.py
"""Unit tests for visitor classes and Mermaid diagram generator."""

from graph_query_engine.optimizer import (
    PhysicalPlan,
    OptimizedPhysicalPlan,
    PlanComparisonVisitor,
    ValidationVisitor,
    MermaidDiagramVisitor,
    FilterPushdownRule,
)


def test_plan_comparison_visitor():
    before = PhysicalPlan(operators=[{"type": "scan", "params": {}}, {"type": "filter", "params": {}}])
    after = OptimizedPhysicalPlan(operators=[{"type": "index_scan", "params": {}}])

    visitor = PlanComparisonVisitor()
    summary = visitor.compare(before, after)

    assert summary["before_operator_count"] == 2
    assert summary["after_operator_count"] == 1
    assert summary["operator_delta"] == -1


def test_mermaid_diagram_visitor():
    plan = PhysicalPlan(operators=[{"type": "scan", "params": {}}, {"type": "filter", "params": {}}])
    visitor = MermaidDiagramVisitor()
    diagram = visitor.visit_plan(plan)
    assert "graph TD" in diagram
    assert "scan" in diagram
    assert "filter" in diagram
