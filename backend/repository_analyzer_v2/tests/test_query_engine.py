"""
tests/test_query_engine.py
---------------------------
Unit tests for CallGraphQueryEngine — verifying all 11 O(1) indexed public query APIs.
"""

from models.graph_models import CallGraph, CallGraphEdge, CallGraphNode, CallGraphResult
from analysis.call_graph.graph_index import CallGraphIndexBuilder


class TestCallGraphQueryEngine:
    def setup_method(self):
        n1 = CallGraphNode(symbol_id="sym-main", fully_qualified_name="app.main.main", name="main", file_path="app/main.py")
        n2 = CallGraphNode(symbol_id="sym-auth", fully_qualified_name="app.auth.login", name="login", file_path="app/auth.py")
        n3 = CallGraphNode(symbol_id="sym-db", fully_qualified_name="app.db.save", name="save", file_path="app/db.py")

        e1 = CallGraphEdge(caller_symbol_id="sym-main", callee_symbol_id="sym-auth", caller_fqn="app.main.main", callee_fqn="app.auth.login", file_path="app/main.py")
        e2 = CallGraphEdge(caller_symbol_id="sym-auth", callee_symbol_id="sym-db", caller_fqn="app.auth.login", callee_fqn="app.db.save", file_path="app/auth.py")

        graph = CallGraph(
            nodes={"sym-main": n1, "sym-auth": n2, "sym-db": n3},
            edges={e1.edge_id: e1, e2.edge_id: e2},
            adjacency_list={"sym-main": ["sym-auth"], "sym-auth": ["sym-db"]},
            reverse_adjacency_list={"sym-auth": ["sym-main"], "sym-db": ["sym-auth"]},
            node_count=3,
            edge_count=2,
        )

        cg_result = CallGraphResult(repository_id="repo1", graph=graph)
        builder = CallGraphIndexBuilder(repository_id="repo1")
        index_result = builder.build_index(cg_result)

        self.engine = index_result.query_engine
        self.n1 = n1
        self.n2 = n2
        self.n3 = n3
        self.e1 = e1
        self.e2 = e2

    def test_find_node_by_symbol_id(self):
        node = self.engine.find_node("sym-auth")
        assert node == self.n2

        assert self.engine.find_node("missing") is None

    def test_find_node_by_fqn(self):
        node = self.engine.find_node_by_fqn("app.auth.login")
        assert node == self.n2

        assert self.engine.find_node_by_fqn("unknown.fqn") is None

    def test_find_nodes_by_file(self):
        nodes = self.engine.find_nodes_by_file("app/main.py")
        assert nodes == [self.n1]

        # Path normalization check (Windows backslashes vs POSIX)
        nodes_win = self.engine.find_nodes_by_file("app\\main.py")
        assert nodes_win == [self.n1]

    def test_find_callers(self):
        callers = self.engine.find_callers("sym-auth")
        assert callers == ["sym-main"]

        callers_db = self.engine.find_callers("sym-db")
        assert callers_db == ["sym-auth"]

    def test_find_callees(self):
        callees = self.engine.find_callees("sym-main")
        assert callees == ["sym-auth"]

        callees_auth = self.engine.find_callees("sym-auth")
        assert callees_auth == ["sym-db"]

    def test_find_outgoing_edges(self):
        edges = self.engine.find_outgoing_edges("sym-main")
        assert len(edges) == 1
        assert edges[0] == self.e1

    def test_find_incoming_edges(self):
        edges = self.engine.find_incoming_edges("sym-db")
        assert len(edges) == 1
        assert edges[0] == self.e2

    def test_find_edges_in_file(self):
        edges = self.engine.find_edges_in_file("app/auth.py")
        assert edges == [self.e2]

    def test_contains_node(self):
        assert self.engine.contains_node("sym-main")
        assert not self.engine.contains_node("sym-nonexistent")

    def test_contains_edge(self):
        assert self.engine.contains_edge("sym-main", "sym-auth")
        assert self.engine.contains_edge("sym-auth", "sym-db")
        assert not self.engine.contains_edge("sym-main", "sym-db")

    def test_graph_statistics(self):
        stats = self.engine.graph_statistics()
        assert stats["node_count"] == 3
        assert stats["edge_count"] == 2
        assert stats["fqn_indexed_nodes"] == 3
