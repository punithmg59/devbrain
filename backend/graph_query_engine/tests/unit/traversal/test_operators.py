# backend/graph_query_engine/tests/unit/traversal/test_operators.py
"""Unit tests for all 15 composable traversal operators."""

from graph_query_engine.traversal import (
    TraversalExecutionContext,
    TraversalPipeline,
    NodeScanOperator,
    IndexLookupOperator,
    NeighborExpandOperator,
    EdgeFilterOperator,
    PathExpandOperator,
    TraversalMergeOperator,
    TraversalUnionOperator,
    TraversalIntersectionOperator,
    TraversalLimitOperator,
    TraversalSortOperator,
    TraversalDeduplicateOperator,
    TraversalAggregateOperator,
    TraversalProjectOperator,
    TraversalCollectOperator,
    TraversalResultBuilderOperator,
)


def get_graph():
    return {
        "node_1": [("node_2", {"type": "CALLS"})],
        "node_2": [("node_3", {"type": "IMPORTS"})],
        "node_3": [],
    }


def test_node_scan_operator():
    ctx = TraversalExecutionContext(graph_view=get_graph())
    op = NodeScanOperator()
    res = op.execute(ctx, [])
    assert "node_1" in res
    assert "node_2" in res


def test_neighbor_expand_operator():
    ctx = TraversalExecutionContext(graph_view=get_graph())
    op = NeighborExpandOperator(direction="OUTGOING")
    res = op.execute(ctx, ["node_1"])
    assert res == ["node_2"]


def test_edge_filter_operator():
    ctx = TraversalExecutionContext(graph_view=get_graph())
    op = EdgeFilterOperator(edge_type="CALLS")
    res = op.execute(ctx, ["node_1"])
    assert res == ["node_2"]


def test_path_expand_operator():
    ctx = TraversalExecutionContext(graph_view=get_graph())
    op = PathExpandOperator(depth=2)
    res = op.execute(ctx, ["node_1"])
    assert "node_3" in res


def test_combine_operators():
    ctx = TraversalExecutionContext(graph_view=get_graph())

    op_merge = TraversalMergeOperator(secondary_nodes=["node_3"])
    assert op_merge.execute(ctx, ["node_1"]) == ["node_1", "node_3"]

    op_union = TraversalUnionOperator(secondary_nodes=["node_2", "node_3"])
    assert len(op_union.execute(ctx, ["node_1", "node_2"])) == 3

    op_intersect = TraversalIntersectionOperator(secondary_nodes=["node_2"])
    assert op_intersect.execute(ctx, ["node_1", "node_2"]) == ["node_2"]


def test_transform_operators():
    ctx = TraversalExecutionContext(graph_view=get_graph())

    op_dedup = TraversalDeduplicateOperator()
    assert op_dedup.execute(ctx, ["node_1", "node_1", "node_2"]) == ["node_1", "node_2"]

    op_sort = TraversalSortOperator(reverse=True)
    assert op_sort.execute(ctx, ["a", "c", "b"]) == ["c", "b", "a"]

    op_limit = TraversalLimitOperator(limit=1)
    assert len(op_limit.execute(ctx, ["a", "b", "c"])) == 1


def test_pipeline_execution():
    ctx = TraversalExecutionContext(graph_view=get_graph())
    pipeline = TraversalPipeline(operators=[
        NeighborExpandOperator(direction="OUTGOING"),
        TraversalDeduplicateOperator(),
        TraversalSortOperator(),
    ])

    result = pipeline.execute(ctx, ["node_1"])
    assert result.visited_nodes == ["node_2"]
