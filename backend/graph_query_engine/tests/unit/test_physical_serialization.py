"""
Unit test suite for PhysicalPlan serializers (JSON, YAML, Binary).
"""

from graph_query_engine.physical import (
    BinaryPhysicalPlanSerializer,
    JSONPhysicalPlanSerializer,
    PhysicalPlanBuilder,
    YAMLPhysicalPlanSerializer,
)


def test_physical_serialization_roundtrips():
    plan = PhysicalPlanBuilder().with_index_lookup("sym_ser_1").build()

    # 1. JSON
    json_serializer = JSONPhysicalPlanSerializer()
    json_str = json_serializer.serialize(plan)
    restored_json = json_serializer.deserialize(json_str)
    assert restored_json.plan_id == plan.plan_id
    assert restored_json.logical_plan_id == plan.logical_plan_id

    # 2. YAML
    yaml_serializer = YAMLPhysicalPlanSerializer()
    yaml_str = yaml_serializer.serialize(plan)
    restored_yaml = yaml_serializer.deserialize(yaml_str)
    assert restored_yaml.plan_id == plan.plan_id

    # 3. Binary
    bin_serializer = BinaryPhysicalPlanSerializer()
    raw_bytes = bin_serializer.serialize_bytes(plan)
    restored_bin = bin_serializer.deserialize_bytes(raw_bytes)
    assert restored_bin.plan_id == plan.plan_id
