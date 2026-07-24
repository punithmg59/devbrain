"""
tests/test_graph_index_validator.py
------------------------------------
Unit tests for GraphIndexValidator — verifying index completeness and consistency against source CallGraph objects.
"""

from models.graph_models import CallGraph, CallGraphNode
from models.graph_index_models import GraphIndex
from analysis.call_graph.index_validator import GraphIndexValidator


class TestGraphIndexValidator:
    def test_valid_index_passes_validation(self):
        n1 = CallGraphNode(symbol_id="node-1", fully_qualified_name="app.a", name="a")
        graph = CallGraph(nodes={"node-1": n1}, node_count=1)

        graph_index = GraphIndex(
            node_by_symbol_id={"node-1": n1},
            node_by_fqn={"app.a": n1},
        )

        validator = GraphIndexValidator()
        report = validator.validate(graph_index, graph)

        assert report.is_valid
        assert report.error_count == 0

    def test_missing_indexed_node_detected(self):
        n1 = CallGraphNode(symbol_id="node-1", fully_qualified_name="app.a", name="a")
        # graph is empty, but index claims node-1 is present
        graph = CallGraph(nodes={}, node_count=0)

        graph_index = GraphIndex(
            node_by_symbol_id={"node-1": n1},
        )

        validator = GraphIndexValidator()
        report = validator.validate(graph_index, graph)

        assert not report.is_valid
        assert report.error_count == 1
        assert report.issues[0].code == "MISSING_INDEXED_NODE"
