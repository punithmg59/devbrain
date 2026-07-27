"""
Unit tests for Public Query API versioning.
"""

from graph_query_engine.api.version import QueryVersion


def test_query_version_defaults():
    ver = QueryVersion()
    assert ver.major == 1
    assert ver.minor == 0
    assert ver.patch == 0
    assert ver.to_tuple() == (1, 0, 0)
    assert str(ver) == "1.0.0-v1.0"
