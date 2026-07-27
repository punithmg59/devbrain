"""
Unit tests for Public Query API QueryRequest and QueryResponse models.
"""

from graph_query_engine.api.request import QueryRequest
from graph_query_engine.api.response import QueryResponse, ResponseStatus
from graph_query_engine.api.result import QueryResult, QueryStatistics, QueryDiagnostics


def test_request_response_models():
    req = QueryRequest(operation="lookup_node", target="node_123")
    assert req.operation == "lookup_node"
    assert req.target == "node_123"
    assert req.request_id.startswith("req_")

    res = QueryResponse(
        request_id=req.request_id,
        status=ResponseStatus.SUCCESS,
        result=QueryResult(target="node_123", nodes=[{"id": "node_123"}]),
        statistics=QueryStatistics(planning_time_ms=1.5, execution_time_ms=5.0),
        diagnostics=QueryDiagnostics(query_summary="lookup node_123"),
    )

    assert res.request_id == req.request_id
    assert res.status == ResponseStatus.SUCCESS
    assert len(res.result.nodes) == 1
    assert res.result.nodes[0]["id"] == "node_123"
    assert res.statistics.planning_time_ms == 1.5
