# backend/graph_query_engine/tests/unit/traversal/test_serialization.py
"""Unit tests for JSON, YAML, and Binary serializers for TraversalResult."""

from graph_query_engine.traversal import (
    TraversalResult,
    JSONTraversalSerializer,
    YAMLTraversalSerializer,
    BinaryTraversalSerializer,
)


def test_json_serialization():
    res = TraversalResult(visited_nodes=["n1", "n2"], root_nodes=["n1"], execution_time_ms=12.3)
    json_str = JSONTraversalSerializer.serialize(res)
    assert '"visited_nodes"' in json_str

    deserialized = JSONTraversalSerializer.deserialize(json_str)
    assert deserialized.visited_nodes == ["n1", "n2"]


def test_yaml_serialization():
    res = TraversalResult(visited_nodes=["n1", "n2"], root_nodes=["n1"])
    yaml_str = YAMLTraversalSerializer.serialize(res)
    assert "visited_nodes" in yaml_str

    deserialized = YAMLTraversalSerializer.deserialize(yaml_str)
    assert deserialized.visited_nodes == ["n1", "n2"]


def test_binary_serialization():
    res = TraversalResult(visited_nodes=["n1", "n2"], root_nodes=["n1"])
    raw_bytes = BinaryTraversalSerializer.serialize(res)
    assert isinstance(raw_bytes, bytes)

    deserialized = BinaryTraversalSerializer.deserialize(raw_bytes)
    assert deserialized.visited_nodes == ["n1", "n2"]
