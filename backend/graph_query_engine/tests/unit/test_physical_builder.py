"""
Unit test suite for fluent PhysicalPlanBuilder immutability.
"""

from graph_query_engine.physical import PhysicalPlanBuilder


def test_physical_builder_immutability():
    b1 = PhysicalPlanBuilder().with_index_lookup("sym_b1")
    b2 = b1.with_logical_plan_id("lplan_custom")

    p1 = b1.build()
    p2 = b2.build()

    assert p1.logical_plan_id == "lplan_default"
    assert p2.logical_plan_id == "lplan_custom"
