"""
Unit test suite for fluent LogicalPlanBuilder immutability.
"""

from graph_query_engine.logical import LogicalPlanBuilder
from graph_query_engine.query import PredicateBuilder


def test_logical_builder_immutability():
    b1 = LogicalPlanBuilder().with_lookup("sym_100")
    b2 = b1.with_filter(PredicateBuilder.eq("kind", "CLASS"))
    b3 = b2.with_limit(20)

    p1 = b1.build()
    p2 = b2.build()
    p3 = b3.build()

    assert p1.root_node.operator.operator_name == "LOGICAL_LOOKUP"
    assert p2.root_node.operator.operator_name == "LOGICAL_FILTER"
    assert p3.root_node.operator.operator_name == "LOGICAL_LIMIT"
    assert p3.metadata.node_count == 3
