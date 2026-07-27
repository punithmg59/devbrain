"""
Unit test suite for fluent ExecutionPlanBuilder immutability.
"""

from graph_query_engine.execution import ExecutionPlanBuilder


def test_execution_builder_immutability():
    b1 = ExecutionPlanBuilder().with_physical_plan_id("pplan_100")
    b2 = b1.with_timeout_ms(60_000)

    p1 = b1.build()
    p2 = b2.build()

    assert p1.metadata.timeout_ms == 30_000
    assert p2.metadata.timeout_ms == 60_000
