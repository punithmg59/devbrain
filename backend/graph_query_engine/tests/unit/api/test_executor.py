"""
Unit tests for Public Query API QueryExecutor.
"""

from graph_query_engine.api.executor import QueryExecutor
from graph_query_engine.api.request import QueryRequest
from graph_query_engine.api.response import ResponseStatus


class MockGraphView:
    def __init__(self):
        self.adj = {"NodeA": [("NodeB", {})], "NodeB": [("NodeC", {})], "NodeC": []}
        self.nodes = {"NodeA": {"id": "NodeA"}, "NodeB": {"id": "NodeB"}, "NodeC": {"id": "NodeC"}}

    def get_all_nodes(self):
        return list(self.nodes.keys())

    def get_node(self, node_id):
        return self.nodes.get(node_id)

    def get_neighbors(self, node_id, direction=None):
        return [nbr for nbr, meta in self.adj.get(node_id, [])]


def test_executor_end_to_end():
    executor = QueryExecutor()
    mock_graph = MockGraphView()

    req = QueryRequest(operation="find_callers", target="NodeA")
    res = executor.execute(req, graph_view=mock_graph)

    assert res.status == ResponseStatus.SUCCESS
    assert res.statistics.planning_time_ms >= 0.0
    assert res.statistics.execution_time_ms >= 0.0
    assert len(res.result.nodes) > 0
    assert "NodeA" in [n["id"] for n in res.result.nodes]
