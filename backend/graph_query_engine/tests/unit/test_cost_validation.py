"""
Unit test suite for CostValidator rules.
"""

from graph_query_engine.cost import CostEstimate, CostReport, CostValidator
from graph_query_engine.types import QueryId


def test_cost_validator_report():
    est = CostEstimate(cpu_cost=50.0, memory_cost=1024.0, confidence_score=0.9)
    report = CostReport(
        plan_id="lplan_valid",
        query_id=QueryId("qry_valid"),
        total_cost_estimate=est,
    )

    val_report = CostValidator.validate_report(report)
    assert val_report.is_valid is True
    assert len(val_report.violations) == 0
