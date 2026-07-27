# backend/graph_query_engine/tests/unit/traversal/test_algorithms.py
"""Unit tests for all 10 graph algorithms."""

from graph_query_engine.traversal import (
    TraversalExecutionContext,
    BreadthFirstSearch,
    DepthFirstSearch,
    BidirectionalSearch,
    ReachabilityAnalysis,
    ShortestPath,
    ConnectedComponents,
    TopologicalTraversal,
    CycleDetection,
    AncestorDiscovery,
    DescendantDiscovery,
    NeighborhoodExpansion,
)


def get_sample_graph():
    # A -> B -> C -> D
    # A -> E -> F
    # C -> A (cycle)
    return {
        "A": [("B", {"type": "CALLS"}), ("E", {"type": "IMPORTS"})],
        "B": [("C", {"type": "CALLS"})],
        "C": [("D", {"type": "CALLS"}), ("A", {"type": "CALLS"})],
        "D": [],
        "E": [("F", {"type": "IMPORTS"})],
        "F": [],
    }


def test_bfs_algorithm():
    graph = get_sample_graph()
    ctx = TraversalExecutionContext(graph_view=graph)
    algo = BreadthFirstSearch()

    result = algo.execute(ctx, start_nodes=["A"], max_depth=2)

    assert "A" in result.visited_nodes
    assert "B" in result.visited_nodes
    assert "E" in result.visited_nodes
    assert "C" in result.visited_nodes
    assert result.depth_map["A"] == 0
    assert result.depth_map["B"] == 1


def test_dfs_algorithm():
    graph = get_sample_graph()
    ctx = TraversalExecutionContext(graph_view=graph)
    algo = DepthFirstSearch()

    result = algo.execute(ctx, start_nodes=["A"], max_depth=3)

    assert "A" in result.visited_nodes
    assert len(result.paths) > 0


def test_bidirectional_search():
    graph = get_sample_graph()
    ctx = TraversalExecutionContext(graph_view=graph)
    algo = BidirectionalSearch()

    result = algo.execute(ctx, start_nodes=["A"], target_node="C")

    assert len(result.paths) == 1
    assert result.paths[0].nodes == ["A", "B", "C"]


def test_reachability_analysis():
    graph = get_sample_graph()
    ctx = TraversalExecutionContext(graph_view=graph)
    algo = ReachabilityAnalysis()

    result = algo.execute(ctx, start_nodes=["A"], target_nodes=["C", "F", "UNKNOWN"])

    assert "C" in result.leaf_nodes
    assert "F" in result.leaf_nodes
    assert "UNKNOWN" not in result.leaf_nodes


def test_shortest_path():
    graph = get_sample_graph()
    ctx = TraversalExecutionContext(graph_view=graph)
    algo = ShortestPath()

    result = algo.execute(ctx, start_nodes=["A"], target_node="D")

    assert len(result.paths) == 1
    assert result.paths[0].nodes == ["A", "B", "C", "D"]


def test_connected_components():
    graph = get_sample_graph()
    ctx = TraversalExecutionContext(graph_view=graph)
    algo = ConnectedComponents()

    result = algo.execute(ctx, start_nodes=["A"])

    assert len(result.visited_nodes) >= 6


def test_topological_traversal():
    # DAG: X -> Y -> Z
    dag = {"X": ["Y"], "Y": ["Z"], "Z": []}
    ctx = TraversalExecutionContext(graph_view=dag)
    algo = TopologicalTraversal()

    result = algo.execute(ctx, start_nodes=["X"])

    assert result.visited_nodes == ["X", "Y", "Z"]


def test_cycle_detection():
    graph = get_sample_graph()
    ctx = TraversalExecutionContext(graph_view=graph)
    algo = CycleDetection()

    result = algo.execute(ctx, start_nodes=["A"])

    assert len(result.paths) > 0  # Should detect A -> B -> C -> A cycle


def test_ancestry_discovery():
    graph = get_sample_graph()
    ctx = TraversalExecutionContext(graph_view=graph)

    desc_algo = DescendantDiscovery()
    desc_res = desc_algo.execute(ctx, start_nodes=["A"])
    assert "B" in desc_res.visited_nodes
    assert "E" in desc_res.visited_nodes

    anc_algo = AncestorDiscovery()
    anc_res = anc_algo.execute(ctx, start_nodes=["C"])
    assert "B" in anc_res.visited_nodes


def test_neighborhood_expansion():
    graph = get_sample_graph()
    ctx = TraversalExecutionContext(graph_view=graph)
    algo = NeighborhoodExpansion()

    result = algo.execute(ctx, start_nodes=["B"], k_hops=1)

    assert "C" in result.visited_nodes
