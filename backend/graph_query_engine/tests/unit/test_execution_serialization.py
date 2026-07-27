"""
Unit test suite for ExecutionPlan serializers (JSON, YAML, Binary).
"""

from graph_query_engine.execution import (
    BinaryExecutionPlanSerializer,
    ExecutionPlanBuilder,
    JSONExecutionPlanSerializer,
    YAMLExecutionPlanSerializer,
)


def test_execution_serialization_roundtrips():
    plan = ExecutionPlanBuilder().with_physical_plan_id("pplan_ser_1").build()

    # 1. JSON
    json_serializer = JSONExecutionPlanSerializer()
    json_str = json_serializer.serialize(plan)
    restored_json = json_serializer.deserialize(json_str)
    assert restored_json.execution_plan_id == plan.execution_plan_id
    assert restored_json.physical_plan_id == plan.physical_plan_id

    # 2. YAML
    yaml_serializer = YAMLExecutionPlanSerializer()
    yaml_str = yaml_serializer.serialize(plan)
    restored_yaml = yaml_serializer.deserialize(yaml_str)
    assert restored_yaml.execution_plan_id == plan.execution_plan_id

    # 3. Binary
    bin_serializer = BinaryExecutionPlanSerializer()
    raw_bytes = bin_serializer.serialize_bytes(plan)
    restored_bin = bin_serializer.deserialize_bytes(raw_bytes)
    assert restored_bin.execution_plan_id == plan.execution_plan_id
