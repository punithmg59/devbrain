# backend/graph_query_engine/tests/unit/traversal/test_large_repository.py
"""Large repository graph traversal test (1,000+ nodes, multi-hop traversals).
"""

from graph_query_engine.traversal import (
    TraversalEngine,
    TraversalLimits,
)


def generate_large_synthetic_repository(num_nodes: int = 1000):
    """Generates a synthetic repository graph with linear, branching, and cross-dependency edges."""
    graph = {}
    for i in range(num_nodes):
        node_id = f"file_{i}.py"
        neighbors = []
        # Main chain
        if i + 1 < num_nodes:
            neighbors.append((f"file_{i+1}.py", {"type": "IMPORTS"}))
        # Skip chain (branching factor)
        if i + 5 < num_nodes:
            neighbors.append((f"file_{i+5}.py", {"type": "CALLS"}))
        graph[node_id] = neighbors
    return graph


def test_large_repository_traversal_bfs():
    num_nodes = 1200
    graph = generate_large_synthetic_repository(num_nodes=num_nodes)
    engine = TraversalEngine()

    limits = TraversalLimits(max_depth=50, max_nodes=500)
    result = engine.execute_algorithm(
        algorithm="bfs",
        graph_view=graph,
        start_nodes=["file_0.py"],
        limits=limits,
    )

    assert len(result.visited_nodes) <= 500
    assert result.metrics.execution_duration_ms > 0
    assert len(result.paths) > 0


def test_large_repository_connected_components():
    graph = generate_large_synthetic_repository(num_nodes=1000)
    engine = TraversalEngine()

    result = engine.execute_algorithm(
        algorithm="connected_components",
        graph_view=graph,
        start_nodes=["file_0.py"],
    )

    assert len(result.visited_nodes) == 1000
