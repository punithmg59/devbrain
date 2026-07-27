# backend/graph_query_engine/tests/unit/traversal/test_visitor.py
"""Unit tests for visitors and MermaidGraphVisitor diagram generator."""

from graph_query_engine.traversal import (
    TraversalPath,
    TraversalResult,
    TraversalInspectionVisitor,
    TraversalPrintingVisitor,
    MermaidGraphVisitor,
)


def test_inspection_and_printing_visitor():
    path = TraversalPath(nodes=["A", "B", "C"], depth=2)
    res = TraversalResult(visited_nodes=["A", "B", "C"], paths=[path], root_nodes=["A"])

    insp = TraversalInspectionVisitor()
    info = insp.visit_result(res)
    assert info["visited_node_count"] == 3
    assert info["path_count"] == 1

    prn = TraversalPrintingVisitor()
    output = prn.visit_result(res)
    assert "TraversalResult" in output
    assert "A -> B -> C" in output


def test_mermaid_graph_visitor():
    path = TraversalPath(nodes=["NodeA", "NodeB", "NodeC"], depth=2)
    res = TraversalResult(visited_nodes=["NodeA", "NodeB", "NodeC"], paths=[path], root_nodes=["NodeA"])

    visitor = MermaidGraphVisitor()
    mermaid_text = visitor.visit_result(res)

    assert "graph TD" in mermaid_text
    assert "NodeA --> NodeB" in mermaid_text
    assert "NodeB --> NodeC" in mermaid_text
