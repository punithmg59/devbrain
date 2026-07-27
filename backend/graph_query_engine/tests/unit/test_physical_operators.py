"""
Unit test suite for Physical Operators, immutability, and Physical Visitors.
"""

import pytest
from pydantic import ValidationError

from graph_query_engine.physical import (
    IndexLookupPhysicalOperator,
    PhysicalOperatorBuilder,
    PhysicalPlanBuilder,
    PrintPhysicalVisitor,
)


def test_physical_operator_immutability():
    op = IndexLookupPhysicalOperator(operator_id="op_p_1", index_name="PRIMARY_INDEX")
    assert op.operator_name == "INDEX_LOOKUP"

    with pytest.raises((ValidationError, TypeError)):
        op.index_name = "MUTATED_INDEX"


def test_physical_visitor_print_tree():
    plan = PhysicalPlanBuilder().with_index_lookup("sym_vis").build()
    visitor = PrintPhysicalVisitor()
    tree_text = visitor.print_plan(plan)

    assert "INDEX_LOOKUP" in tree_text
