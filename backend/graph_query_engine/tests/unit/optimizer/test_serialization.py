# backend/graph_query_engine/tests/unit/optimizer/test_serialization.py
"""Unit tests for JSON, YAML, and Binary serializers."""

from graph_query_engine.optimizer import (
    PhysicalPlan,
    OptimizedPhysicalPlan,
    JSONOptimizerSerializer,
    YAMLOptimizerSerializer,
    BinaryOptimizerSerializer,
)


def test_json_serialization():
    plan = PhysicalPlan(operators=[{"type": "scan", "params": {"id": 1}}])
    json_str = JSONOptimizerSerializer.serialize(plan)
    assert '"type": "scan"' in json_str

    deserialized = JSONOptimizerSerializer.deserialize_physical_plan(json_str)
    assert deserialized.operators[0]["params"]["id"] == 1


def test_yaml_serialization():
    plan = PhysicalPlan(operators=[{"type": "filter", "params": {"pred": "x > 0"}}])
    yaml_str = YAMLOptimizerSerializer.serialize(plan)
    assert "filter" in yaml_str

    deserialized = YAMLOptimizerSerializer.deserialize_physical_plan(yaml_str)
    assert deserialized.operators[0]["type"] == "filter"


def test_binary_serialization():
    plan = PhysicalPlan(operators=[{"type": "sort", "params": {}}])
    raw_bytes = BinaryOptimizerSerializer.serialize(plan)
    assert isinstance(raw_bytes, bytes)

    deserialized = BinaryOptimizerSerializer.deserialize_physical_plan(raw_bytes)
    assert deserialized.operators[0]["type"] == "sort"
