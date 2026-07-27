# backend/graph_query_engine/tests/unit/traversal/test_builder.py
"""Unit tests for fluent builders."""

from graph_query_engine.traversal import (
    TraversalResultBuilder,
    ExecutionContextBuilder,
    TraversalReportBuilder,
    TraversalMetricsBuilder,
    TraversalLimits,
)


def test_traversal_result_builder():
    builder = TraversalResultBuilder()
    res = (
        builder.with_visited_nodes(["A", "B"])
        .with_root_nodes(["A"])
        .with_execution_time_ms(15.2)
        .build()
    )

    assert res.visited_nodes == ["A", "B"]
    assert res.root_nodes == ["A"]
    assert res.execution_time_ms == 15.2


def test_execution_context_builder():
    builder = ExecutionContextBuilder()
    ctx = builder.with_graph_view({"A": []}).with_limits(TraversalLimits(max_depth=10)).build()

    assert ctx.graph_view == {"A": []}
    assert ctx.limits.max_depth == 10


def test_report_and_metrics_builder():
    res = TraversalResultBuilder().with_visited_nodes(["A"]).with_root_nodes(["A"]).build()
    report = TraversalReportBuilder().with_result(res).build()

    assert report["visited_node_count"] == 1

    metrics = TraversalMetricsBuilder().add_nodes_visited(5).add_edges_visited(10).build()
    assert metrics.nodes_visited == 5
    assert metrics.edges_visited == 10
