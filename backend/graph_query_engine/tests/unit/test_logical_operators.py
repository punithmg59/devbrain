"""
Unit test suite for Logical Operators, immutability, and Logical Visitors.
"""

import pytest
from pydantic import ValidationError

from graph_query_engine.logical import (
    LogicalLookupOperator,
    LogicalOperatorBuilder,
    LogicalPlanBuilder,
    PrintLogicalVisitor,
)


def test_logical_operator_immutability():
    op = LogicalOperatorBuilder.lookup("sym_1", name="fn_test")
    assert op.operator_name == "LOGICAL_LOOKUP"

    with pytest.raises((ValidationError, TypeError)):
        op.operator_name = "MUTATED"


def test_logical_visitor_print_tree():
    plan = (
        LogicalPlanBuilder()
        .with_lookup("sym_vis_1", name="vis_fn")
        .with_projection("id", "name")
        .with_limit(10)
        .build()
    )

    visitor = PrintLogicalVisitor()
    tree_text = visitor.print_plan(plan)

    assert "LOGICAL_LIMIT" in tree_text
    assert "LOGICAL_PROJECTION" in tree_text
    assert "LOGICAL_LOOKUP" in tree_text
