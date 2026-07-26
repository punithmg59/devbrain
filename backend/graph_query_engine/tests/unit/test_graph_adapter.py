"""
Unit tests for GraphAdapter.
"""

from types import SimpleNamespace
from graph_query_engine.adapter import GraphAdapter
from graph_query_engine.types import NodeId, RelationshipType


def test_graph_adapter_transformation():
    # Mock DependencyGraph object
    sym1 = SimpleNamespace(
        symbol_id="sym_1",
        display_name="func_a",
        canonical_string="app.services.func_a",
        kind="FUNCTION",
        file_path="app/services.py",
    )
    sym2 = SimpleNamespace(
        symbol_id="sym_2",
        display_name="func_b",
        canonical_string="app.services.func_b",
        kind="FUNCTION",
        file_path="app/services.py",
    )
    edge1 = SimpleNamespace(
        edge_id="e_1",
        source_id="sym_1",
        target_id="sym_2",
        kind="CALLS",
    )

    mock_graph = SimpleNamespace(
        repository_id="repo_100",
        version="4.6.0",
        canonical_symbols=SimpleNamespace(symbols=[sym1, sym2]),
        edges=[edge1],
        statistics=SimpleNamespace(node_count=2, edge_count=1),
    )

    view = GraphAdapter.adapt(mock_graph)

    assert str(view.repository_id) == "repo_100"
    assert len(view.nodes) == 2
    assert len(view.edges) == 1

    node1 = view.get_node_view(NodeId("sym_1"))
    assert node1 is not None
    assert node1.name == "func_a"

    neighbors = list(view.get_neighbors(NodeId("sym_1"), RelationshipType.CALLS))
    assert neighbors == ["sym_2"]
