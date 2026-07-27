"""
Fluent Immutable Query Builders.

Constructs EngineeringQuery instances without side-effects, planning, or graph access.
100% Immutable builder pattern - every method call returns a new updated builder/query object.
"""

import uuid
from typing import Any, Dict, List, Optional, Tuple
from pydantic import BaseModel, ConfigDict, Field

from graph_query_engine.query.ast import ASTNodeType, QueryAST, QueryASTNode
from graph_query_engine.query.constraints import QueryConstraints, TimeBudgetConstraint
from graph_query_engine.query.expressions import (
    ComparisonExpression,
    LiteralExpression,
    PropertyAccessExpression,
    QueryExpression,
)
from graph_query_engine.query.model import (
    EngineeringQuery,
    PlannerQueryOptions,
    QueryMetadata,
    QueryOptions,
    SourceInfo,
)
from graph_query_engine.query.operators import (
    FilterOperator,
    LookupOperator,
    QueryOperator,
)
from graph_query_engine.query.predicates import (
    AndPredicate,
    EqualityPredicate,
    QueryPredicate,
)
from graph_query_engine.query.references import EntityReference, SymbolReference
from graph_query_engine.query.result import ResultProjection, ResultSpecification
from graph_query_engine.types import QueryId, SymbolId


class ExpressionBuilder:
    """Helper builder for constructing query expressions fluently."""

    @staticmethod
    def literal(val: Any) -> LiteralExpression:
        """Constructs a LiteralExpression."""
        val_type = type(val).__name__.upper()
        return LiteralExpression(value=val, value_type=val_type)

    @staticmethod
    def property(target: str, prop: str) -> PropertyAccessExpression:
        """Constructs a PropertyAccessExpression."""
        return PropertyAccessExpression(target=target, property_name=prop)

    @staticmethod
    def equals(left: QueryExpression, right: QueryExpression) -> ComparisonExpression:
        """Constructs an equality ComparisonExpression."""
        return ComparisonExpression(left=left, operator="=", right=right)


class PredicateBuilder:
    """Helper builder for constructing query predicates fluently."""

    @staticmethod
    def eq(property_name: str, value: Any) -> EqualityPredicate:
        """Constructs an EqualityPredicate."""
        return EqualityPredicate(property_name=property_name, expected_value=value)

    @staticmethod
    def and_combine(*predicates: QueryPredicate) -> AndPredicate:
        """Combines predicates using AndPredicate."""
        return AndPredicate(predicates=tuple(predicates))


class ASTBuilder:
    """Helper builder for constructing QueryAST trees fluently."""

    @staticmethod
    def create_node(
        content: Any,
        children: Tuple[QueryASTNode, ...] = (),
        node_id: Optional[str] = None,
    ) -> QueryASTNode:
        """Creates a QueryASTNode wrapper."""
        nid = node_id or f"node_{uuid.uuid4().hex[:8]}"
        ntype = ASTNodeType.OPERATOR
        if isinstance(content, QueryExpression):
            ntype = ASTNodeType.EXPRESSION
        elif isinstance(content, QueryPredicate):
            ntype = ASTNodeType.PREDICATE
        elif isinstance(content, EntityReference):
            ntype = ASTNodeType.REFERENCE
        return QueryASTNode(
            node_id=nid,
            node_type=ntype,
            content=content,
            children=children,
        )

    @staticmethod
    def create_ast(root_node: QueryASTNode, ast_id: Optional[str] = None) -> QueryAST:
        """Creates a QueryAST tree container."""
        aid = ast_id or f"ast_{uuid.uuid4().hex[:8]}"
        return QueryAST(ast_id=aid, root_node=root_node, node_count=1 + len(root_node.children))


class QueryBuilder:
    """
    Fluent immutable builder for constructing EngineeringQuery instances.

    Each mutation method returns a NEW QueryBuilder instance.
    """

    def __init__(
        self,
        name: str = "EngineeringQuery",
        root_content: Optional[Any] = None,
    ) -> None:
        self._name = name
        self._root_content = root_content or LookupOperator(
            target_reference=SymbolReference(identifier="sym_default", name="default")
        )
        self._children: Tuple[QueryASTNode, ...] = ()
        self._time_budget_sec: float = 30.0
        self._projected_fields: Tuple[str, ...] = ()

    def with_name(self, name: str) -> "QueryBuilder":
        """Returns a new QueryBuilder with updated query name."""
        qb = self._copy()
        qb._name = name
        return qb

    def with_lookup(self, symbol_id_str: str, name: str = "") -> "QueryBuilder":
        """Returns a new QueryBuilder with a LookupOperator root content."""
        qb = self._copy()
        ref = SymbolReference(identifier=symbol_id_str, symbol_id=SymbolId(symbol_id_str), name=name or symbol_id_str)
        qb._root_content = LookupOperator(target_reference=ref)
        return qb

    def with_filter(self, predicate: QueryPredicate) -> "QueryBuilder":
        """Returns a new QueryBuilder wrapping current root in a FilterOperator."""
        qb = self._copy()
        filter_op = FilterOperator(predicate=predicate)
        curr_node = ASTBuilder.create_node(qb._root_content, children=qb._children)
        qb._root_content = filter_op
        qb._children = (curr_node,)
        return qb

    def with_time_budget(self, seconds: float) -> "QueryBuilder":
        """Returns a new QueryBuilder with updated time budget."""
        qb = self._copy()
        qb._time_budget_sec = seconds
        return qb

    def with_projection(self, *fields: str) -> "QueryBuilder":
        """Returns a new QueryBuilder with projected fields."""
        qb = self._copy()
        qb._projected_fields = tuple(fields)
        return qb

    def build(self) -> EngineeringQuery:
        """
        Builds and returns the immutable EngineeringQuery instance.
        """
        root_node = ASTBuilder.create_node(self._root_content, children=self._children)
        ast = ASTBuilder.create_ast(root_node)

        constraints = QueryConstraints(
            time_budget=TimeBudgetConstraint(max_seconds=self._time_budget_sec)
        )
        result_spec = ResultSpecification(
            projection=ResultProjection(projected_fields=self._projected_fields)
        )

        return EngineeringQuery(
            metadata=QueryMetadata(name=self._name),
            constraints=constraints,
            result_spec=result_spec,
            ast=ast,
        )

    def _copy(self) -> "QueryBuilder":
        qb = QueryBuilder(name=self._name, root_content=self._root_content)
        qb._children = self._children
        qb._time_budget_sec = self._time_budget_sec
        qb._projected_fields = self._projected_fields
        return qb


__all__ = [
    "ExpressionBuilder",
    "PredicateBuilder",
    "ASTBuilder",
    "QueryBuilder",
]
