"""
Unit tests for Public Query API QuerySession.
"""

from graph_query_engine.api.context import QueryContext
from graph_query_engine.api.request import QueryRequest
from graph_query_engine.api.session import QuerySession


def test_session_context_and_history():
    ctx = QueryContext(repository_id="custom_repo")
    session = QuerySession(default_context=ctx)

    assert session.default_context.repository_id == "custom_repo"
    assert len(session.get_history()) == 0

    req = QueryRequest(operation="lookup_node", target="NodeX")
    res = session.execute(req)

    assert res.status.value == "SUCCESS"
    assert len(session.get_history()) == 1

    session.clear_history()
    assert len(session.get_history()) == 0
