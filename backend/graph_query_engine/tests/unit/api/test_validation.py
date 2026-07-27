"""
Unit tests for Public Query API QueryValidation.
"""

from graph_query_engine.api.context import QueryContext
from graph_query_engine.api.request import QueryRequest
from graph_query_engine.api.validation import QueryValidation


def test_validation_success():
    req = QueryRequest(operation="find_callers", target="MySymbol")
    report = QueryValidation.validate(req)
    assert report.is_valid is True
    assert len(report.violations) == 0


def test_validation_unsupported_operation():
    req = QueryRequest(operation="invalid_operation", target="MySymbol")
    report = QueryValidation.validate(req)
    assert report.is_valid is False
    assert any(v.field == "operation" for v in report.violations)


def test_validation_invalid_context_limits():
    ctx = QueryContext(depth_limit=0, timeout_seconds=-1.0)
    req = QueryRequest(operation="lookup_node", context=ctx)
    report = QueryValidation.validate(req)
    assert report.is_valid is False
    fields = [v.field for v in report.violations]
    assert "context.depth_limit" in fields
    assert "context.timeout_seconds" in fields
