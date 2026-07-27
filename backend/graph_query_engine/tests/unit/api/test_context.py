"""
Unit tests for Public Query API QueryContext.
"""

from graph_query_engine.api.context import QueryContext


def test_query_context_immutability_and_with_methods():
    ctx = QueryContext(repository_id="repo1", depth_limit=5)
    assert ctx.repository_id == "repo1"
    assert ctx.depth_limit == 5

    ctx2 = ctx.with_repository("repo2", branch="feature")
    assert ctx2.repository_id == "repo2"
    assert ctx2.branch == "feature"
    assert ctx.repository_id == "repo1"

    ctx3 = ctx.with_limits(depth_limit=20, timeout_seconds=60.0)
    assert ctx3.depth_limit == 20
    assert ctx3.timeout_seconds == 60.0
    assert ctx.depth_limit == 5
