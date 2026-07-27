"""
Unit tests for Public Query API QueryFactory and QueryRegistry.
"""

from graph_query_engine.api.factory import QueryFactory
from graph_query_engine.api.registry import QueryRegistry


def test_query_factory():
    engine = QueryFactory.create_engine()
    assert engine is not None

    session = QueryFactory.create_session()
    assert session is not None


def test_query_registry():
    registry = QueryRegistry()
    handler = lambda req: "ok"
    registry.register_handler("custom_op", handler)

    assert registry.get_handler("custom_op") == handler
    assert "custom_op" in registry.list_handlers()

    registry.register_session("sess_1", "session_object")
    assert registry.get_session("sess_1") == "session_object"
    assert registry.unregister_session("sess_1") is True
    assert registry.get_session("sess_1") is None
