"""
Unit test suite for LogicalPlan serializers (JSON, YAML, Binary).
"""

from graph_query_engine.logical import (
    BinaryLogicalPlanSerializer,
    JSONLogicalPlanSerializer,
    LogicalPlanBuilder,
    YAMLLogicalPlanSerializer,
)


def test_logical_json_serializer_roundtrip():
    plan = (
        LogicalPlanBuilder()
        .with_lookup("sym_json_1", name="json_symbol")
        .with_projection("id", "name")
        .with_limit(15)
        .build()
    )

    serializer = JSONLogicalPlanSerializer()
    json_str = serializer.serialize(plan)
    assert '"operator_name": "LOGICAL_LIMIT"' in json_str

    restored_plan = serializer.deserialize(json_str)
    assert restored_plan.plan_id == plan.plan_id
    assert restored_plan.query_id == plan.query_id
    assert restored_plan.metadata.node_count == plan.metadata.node_count


def test_logical_yaml_and_binary_serializers():
    plan = LogicalPlanBuilder().with_lookup("sym_by_1").build()

    yaml_serializer = YAMLLogicalPlanSerializer()
    yaml_str = yaml_serializer.serialize(plan)
    restored_yaml = yaml_serializer.deserialize(yaml_str)
    assert restored_yaml.plan_id == plan.plan_id

    bin_serializer = BinaryLogicalPlanSerializer()
    raw_bytes = bin_serializer.serialize_bytes(plan)
    restored_bin = bin_serializer.deserialize_bytes(raw_bytes)
    assert restored_bin.plan_id == plan.plan_id
