"""
tests/test_call_graph_validator.py
-----------------------------------
Unit tests for CallGraphValidator — graph node/edge count matching, dangling edge detection, and integrity checks.
"""

from models.graph_models import CallGraph, CallGraphEdge, CallGraphNode
from analysis.call_graph.validator import CallGraphValidator


class TestCallGraphValidator:
    def test_valid_graph_passes_validation(self):
        n1 = CallGraphNode(symbol_id="node-1", fully_qualified_name="app.a", name="a")
        n2 = CallGraphNode(symbol_id="node-2", fully_qualified_name="app.b", name="b")
        e1 = CallGraphEdge(caller_symbol_id="node-1", callee_symbol_id="node-2")

        graph = CallGraph(
            nodes={"node-1": n1, "node-2": n2},
            edges={e1.edge_id: e1},
            adjacency_list={"node-1": ["node-2"]},
            reverse_adjacency_list={"node-2": ["node-1"]},
            node_count=2,
            edge_count=1,
        )

        validator = CallGraphValidator()
        report = validator.validate(graph)

        assert report.is_valid
        assert report.error_count == 0

    def test_node_and_edge_count_mismatch_detected(self):
        graph = CallGraph(
            nodes={},
            edges={},
            node_count=5,  # mismatch
            edge_count=10, # mismatch
        )
        validator = CallGraphValidator()
        report = validator.validate(graph)

        assert not report.is_valid
        assert report.error_count == 2
        codes = [i.code for i in report.issues]
        assert "NODE_COUNT_MISMATCH" in codes
        assert "EDGE_COUNT_MISMATCH" in codes

    def test_dangling_edge_detected(self):
        n1 = CallGraphNode(symbol_id="node-1", fully_qualified_name="app.a", name="a", file_path="app/a.py")
        # edge references node-2 which is missing from nodes dictionary
        e1 = CallGraphEdge(caller_symbol_id="node-1", callee_symbol_id="node-missing")

        graph = CallGraph(
            nodes={"node-1": n1},
            edges={e1.edge_id: e1},
            node_count=1,
            edge_count=1,
        )

        validator = CallGraphValidator()
        report = validator.validate(graph)

        assert not report.is_valid
        assert report.error_count == 1
        codes = [i.code for i in report.issues]
        assert "CALLEE_DOES_NOT_EXIST" in codes or "DANGLING_CALLEE_EDGE" in codes
