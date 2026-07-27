"""
Unit test suite for Query AST nodes, expressions, predicates, operators, and visitors.
"""

import pytest

from graph_query_engine.query import (
    ASTBuilder,
    ASTNodeType,
    AndPredicate,
    BaseQueryVisitor,
    ComparisonExpression,
    EqualityPredicate,
    ExpressionBuilder,
    FilterOperator,
    LiteralExpression,
    LookupOperator,
    PredicateBuilder,
    PrintVisitor,
    PropertyAccessExpression,
    QueryASTNode,
    SymbolReference,
)


def test_ast_node_immutability_and_equality():
    ref = SymbolReference(identifier="sym_123", name="main")
    node = ASTBuilder.create_node(content=ref, node_id="node_1")

    assert node.node_id == "node_1"
    assert node.node_type == ASTNodeType.REFERENCE
    assert node.content.name == "main"

    with pytest.raises(Exception):
        node.node_id = "node_mutated"


def test_expression_and_predicate_hierarchy():
    prop = ExpressionBuilder.property("symbol", "name")
    lit = ExpressionBuilder.literal("process_data")
    comp = ExpressionBuilder.equals(prop, lit)

    assert comp.expression_type == "COMPARISON"
    assert comp.left.property_name == "name"
    assert comp.right.value == "process_data"

    eq_pred = PredicateBuilder.eq("name", "process_data")
    and_pred = PredicateBuilder.and_combine(eq_pred, PredicateBuilder.eq("kind", "FUNCTION"))

    assert and_pred.predicate_type == "AND"
    assert len(and_pred.predicates) == 2


def test_ast_visitor_traversal():
    ref = SymbolReference(identifier="sym_test", name="test_fn")
    lookup = LookupOperator(target_reference=ref)
    child_node = ASTBuilder.create_node(content=lookup, node_id="child_1")

    filter_op = FilterOperator(predicate=EqualityPredicate(property_name="kind", expected_value="FUNCTION"))
    root_node = ASTBuilder.create_node(content=filter_op, children=(child_node,), node_id="root_1")
    ast_tree = ASTBuilder.create_ast(root_node)

    visitor = BaseQueryVisitor()
    visited = visitor.visit_ast(ast_tree)
    assert len(visited) == 2  # Dispatched to filter_op content and child_node

    printer = PrintVisitor()
    tree_text = printer.visit_node(root_node)
    assert "root_1" in printer.print_tree(ast_tree)
