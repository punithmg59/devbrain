"""
tests/test_graph_index_builder.py
----------------------------------
Unit tests for CallGraphIndexBuilder — verifying O(1) index table construction across symbol IDs, FQNs, files, callers, callees, and edges.
"""

from models.graph_models import CallGraph, CallGraphEdge, CallGraphNode, CallGraphResult
from analysis.call_graph.graph_index import CallGraphIndexBuilder


class TestCallGraphIndexBuilder:
    def test_build_index_structure(self):
        n1 = CallGraphNode(symbol_id="sym-1", fully_qualified_name="app.auth.login", name="login", file_path="app/auth.py")
        n2 = CallGraphNode(symbol_id="sym-2", fully_qualified_name="app.models.User", name="User", file_path="app/models.py")
        e1 = CallGraphEdge(caller_symbol_id="sym-1", callee_symbol_id="sym-2", caller_fqn="app.auth.login", callee_fqn="app.models.User", file_path="app/auth.py")

        graph = CallGraph(
            nodes={"sym-1": n1, "sym-2": n2},
            edges={e1.edge_id: e1},
            adjacency_list={"sym-1": ["sym-2"]},
            reverse_adjacency_list={"sym-2": ["sym-1"]},
            node_count=2,
            edge_count=1,
        )

        cg_result = CallGraphResult(repository_id="repo1", graph=graph)
        builder = CallGraphIndexBuilder(repository_id="repo1")
        index_result = builder.build_index(cg_result)

        assert index_result.validation_report.is_valid
        index = index_result.graph_index

        # Check SymbolId index
        assert index.node_by_symbol_id["sym-1"] == n1
        assert index.node_by_symbol_id["sym-2"] == n2

        # Check FQN index
        assert index.node_by_fqn["app.auth.login"] == n1
        assert index.node_by_fqn["app.models.User"] == n2

        # Check File index
        assert n1 in index.nodes_by_file["app/auth.py"]
        assert n2 in index.nodes_by_file["app/models.py"]

        # Check Edges by caller/callee
        assert index.edges_by_caller["sym-1"] == [e1]
        assert index.edges_by_callee["sym-2"] == [e1]

        # Check Callers/Callees lookups
        assert index.callers_index["sym-2"] == ["sym-1"]
        assert index.callees_index["sym-1"] == ["sym-2"]
