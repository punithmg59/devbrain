"""
Unit test suite for Query serializers (JSON, YAML, Binary) and roundtrips.
"""

from graph_query_engine.query import (
    BinaryQuerySerializer,
    JSONQuerySerializer,
    QueryBuilder,
    YAMLQuerySerializer,
)


def test_json_serializer_roundtrip():
    query = (
        QueryBuilder(name="JsonQuery")
        .with_lookup("sym_json_1", name="json_fn")
        .with_projection("id", "name")
        .build()
    )

    serializer = JSONQuerySerializer()
    payload = serializer.serialize(query)
    assert '"name": "JsonQuery"' in payload

    restored_query = serializer.deserialize(payload)
    assert restored_query.query_id == query.query_id
    assert restored_query.metadata.name == "JsonQuery"
    assert restored_query.result_spec.projection.projected_fields == ("id", "name")


def test_yaml_and_binary_serializers():
    query = QueryBuilder(name="BinaryYamlQuery").with_lookup("sym_by_1").build()

    yaml_serializer = YAMLQuerySerializer()
    yaml_str = yaml_serializer.serialize(query)
    restored_yaml = yaml_serializer.deserialize(yaml_str)
    assert restored_yaml.query_id == query.query_id

    bin_serializer = BinaryQuerySerializer()
    raw_bytes = bin_serializer.serialize_bytes(query)
    restored_bin = bin_serializer.deserialize_bytes(raw_bytes)
    assert restored_bin.query_id == query.query_id
