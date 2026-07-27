"""
Unit tests for Public Query API ApiQueryBuilder.
"""

from graph_query_engine.api.builder import ApiQueryBuilder
from graph_query_engine.api.context import QueryContext


def test_api_query_builder_fluent():
    builder = (
        ApiQueryBuilder()
        .operation("find_dependencies")
        .target("MyModule")
        .parameter("depth", 3)
        .context(QueryContext(repository_id="test_repo"))
    )

    req = builder.build()
    assert req.operation == "find_dependencies"
    assert req.target == "MyModule"
    assert req.parameters["depth"] == 3
    assert req.context.repository_id == "test_repo"
