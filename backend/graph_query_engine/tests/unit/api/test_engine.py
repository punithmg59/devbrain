"""
Unit tests for Public Query API QueryEngine facade operations.
"""

import pytest
from graph_query_engine.api.engine import QueryEngine
from graph_query_engine.api.response import ResponseStatus


class MockGraphView:
    def __init__(self):
        self.adj = {"A": [("B", {})], "B": [("C", {})], "C": []}
        self.nodes = {"A": {"id": "A"}, "B": {"id": "B"}, "C": {"id": "C"}}

    def get_all_nodes(self):
        return list(self.nodes.keys())

    def get_node(self, node_id):
        return self.nodes.get(node_id)

    def get_neighbors(self, node_id, direction=None):
        return [nbr for nbr, meta in self.adj.get(node_id, [])]


@pytest.fixture
def engine():
    eng = QueryEngine()
    eng.set_graph_view(MockGraphView())
    return eng


def test_lookups(engine):
    assert engine.lookup_node("A").status == ResponseStatus.SUCCESS
    assert engine.lookup_nodes(["A", "B"]).status == ResponseStatus.SUCCESS
    assert engine.lookup_file("src/main.py").status == ResponseStatus.SUCCESS
    assert engine.lookup_folder("src/").status == ResponseStatus.SUCCESS
    assert engine.lookup_class("UserService").status == ResponseStatus.SUCCESS
    assert engine.lookup_function("process_data").status == ResponseStatus.SUCCESS
    assert engine.lookup_method("save").status == ResponseStatus.SUCCESS
    assert engine.lookup_interface("IRepository").status == ResponseStatus.SUCCESS
    assert engine.lookup_service("AuthService").status == ResponseStatus.SUCCESS
    assert engine.lookup_api("UserAPI").status == ResponseStatus.SUCCESS
    assert engine.lookup_route("/api/v1/users").status == ResponseStatus.SUCCESS
    assert engine.lookup_symbol("my_symbol").status == ResponseStatus.SUCCESS


def test_relationship_finders(engine):
    assert engine.find_callers("A").status == ResponseStatus.SUCCESS
    assert engine.find_callees("A").status == ResponseStatus.SUCCESS
    assert engine.find_dependencies("A").status == ResponseStatus.SUCCESS
    assert engine.find_dependents("A").status == ResponseStatus.SUCCESS
    assert engine.find_imports("A").status == ResponseStatus.SUCCESS
    assert engine.find_exports("A").status == ResponseStatus.SUCCESS
    assert engine.find_neighbors("A").status == ResponseStatus.SUCCESS
    assert engine.find_related_nodes("A").status == ResponseStatus.SUCCESS
    assert engine.find_reachable_nodes("A").status == ResponseStatus.SUCCESS
    assert engine.find_paths("A", "C").status == ResponseStatus.SUCCESS
    assert engine.find_shortest_path("A", "C").status == ResponseStatus.SUCCESS
    assert engine.find_cycles("A").status == ResponseStatus.SUCCESS
    assert engine.find_connected_components().status == ResponseStatus.SUCCESS


def test_searches(engine):
    assert engine.query_repository("SELECT *").status == ResponseStatus.SUCCESS
    assert engine.search_repository("util").status == ResponseStatus.SUCCESS
    assert engine.search_symbols("test_*").status == ResponseStatus.SUCCESS
    assert engine.search_by_name("User*").status == ResponseStatus.SUCCESS
    assert engine.search_by_type("class").status == ResponseStatus.SUCCESS
    assert engine.search_by_metadata("author", "dev").status == ResponseStatus.SUCCESS
    assert engine.search_by_annotation("@Inject").status == ResponseStatus.SUCCESS


def test_executions_and_sessions(engine):
    assert engine.execute_query("test query").status == ResponseStatus.SUCCESS
    assert engine.query("test query string").status == ResponseStatus.SUCCESS

    sess = engine.create_session()
    assert sess.session_id.startswith("sess_")
    retrieved = engine.get_session(sess.session_id)
    assert retrieved.session_id == sess.session_id
