"""
Unit test suite for CostReport serializers (JSON, YAML, Binary).
"""

from graph_query_engine.cost import (
    BinaryCostReportSerializer,
    CostEstimate,
    CostReport,
    JSONCostReportSerializer,
    YAMLCostReportSerializer,
)
from graph_query_engine.types import QueryId


def test_cost_serialization_roundtrips():
    est = CostEstimate(cpu_cost=100.0, memory_cost=2048.0, confidence_score=0.95)
    report = CostReport(
        plan_id="lplan_ser_1",
        query_id=QueryId("qry_ser_1"),
        total_cost_estimate=est,
    )

    # 1. JSON
    json_serializer = JSONCostReportSerializer()
    json_str = json_serializer.serialize(report)
    restored_json = json_serializer.deserialize(json_str)
    assert restored_json.report_id == report.report_id
    assert restored_json.total_cost_estimate.cpu_cost == 100.0

    # 2. YAML
    yaml_serializer = YAMLCostReportSerializer()
    yaml_str = yaml_serializer.serialize(report)
    restored_yaml = yaml_serializer.deserialize(yaml_str)
    assert restored_yaml.report_id == report.report_id

    # 3. Binary
    bin_serializer = BinaryCostReportSerializer()
    raw_bytes = bin_serializer.serialize_bytes(report)
    restored_bin = bin_serializer.deserialize_bytes(raw_bytes)
    assert restored_bin.report_id == report.report_id
