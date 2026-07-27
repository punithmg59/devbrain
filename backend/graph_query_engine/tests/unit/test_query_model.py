"""
Unit test suite for EngineeringQuery representation model and immutability.
"""

import pytest
from pydantic import ValidationError

from graph_query_engine.query import (
    EngineeringQuery,
    QueryBuilder,
    QueryConstraints,
    QueryMetadata,
    QueryOptions,
    QueryVersion,
    SourceInfo,
)


def test_engineering_query_creation():
    builder = QueryBuilder(name="TestQuery").with_lookup("sym_func_1", name="calculate_total")
    query = builder.build()

    assert str(query.query_id).startswith("qry_")
    assert query.metadata.name == "TestQuery"
    assert query.version.schema_version == "1.0.0"
    assert query.ast.root_node is not None


def test_engineering_query_immutability():
    builder = QueryBuilder(name="ImmutableQuery").with_lookup("sym_1")
    query = builder.build()

    with pytest.raises((ValidationError, TypeError)):
        query.metadata = QueryMetadata(name="MutatedName")

    with pytest.raises((ValidationError, TypeError)):
        query.ast = None


def test_query_version_compatibility():
    ver = QueryVersion(schema_version="1.2.0", ast_version="1.0.0")
    assert ver.is_compatible_with("1.0.0") is True
    assert ver.is_compatible_with("2.0.0") is False
    assert "schema_v1.2.0" in str(ver)
