"""
Fluent Immutable Logical Plan Builders.

Constructs LogicalPlan objects step-by-step without side-effects or execution.
100% Immutable builder pattern - every method call returns a new builder/plan object.
"""

import uuid
from typing import Any, Dict, List, Optional, Tuple

from graph_query_engine.logical.operators import (
    LogicalExpandOperator,
    LogicalFilterOperator,
    LogicalLimitOperator,
    LogicalLookupOperator,
    LogicalOperator,
    LogicalProjectionOperator,
)
from graph_query_engine.logical.plan import (
    LogicalPlan,
    LogicalPlanMetadata,
    LogicalPlanNode,
)

from graph_query_engine.query.predicates import QueryPredicate
from graph_query_engine.query.references import EntityReference, SymbolReference
from graph_query_engine.query.traversal import TraversalRequest
from graph_query_engine.types import QueryId, SymbolId


class LogicalOperatorBuilder:
    """Helper builder for constructing individual LogicalOperator nodes."""

    @staticmethod
    def lookup(symbol_id_str: str, name: str = "") -> LogicalLookupOperator:
        """Constructs a LogicalLookupOperator."""
        op_id = f"op_lookup_{uuid.uuid4().hex[:8]}"
        ref = SymbolReference(identifier=symbol_id_str, symbol_id=SymbolId(symbol_id_str), name=name or symbol_id_str)
        return LogicalLookupOperator(
            operator_id=op_id,
            output_schema=("id", "name", "kind"),
            target_reference=ref,
        )

    @staticmethod
    def expand(traversal_request: Optional[TraversalRequest] = None) -> LogicalExpandOperator:
        """Constructs a LogicalExpandOperator."""
        op_id = f"op_expand_{uuid.uuid4().hex[:8]}"
        req = traversal_request or TraversalRequest()
        return LogicalExpandOperator(
            operator_id=op_id,
            output_schema=("source_id", "target_id", "relationship_type"),
            traversal_request=req,
        )

    @staticmethod
    def filter_op(predicate: QueryPredicate, input_fields: Tuple[str, ...] = ()) -> LogicalFilterOperator:
        """Constructs a LogicalFilterOperator."""
        op_id = f"op_filter_{uuid.uuid4().hex[:8]}"
        return LogicalFilterOperator(
            operator_id=op_id,
            output_schema=input_fields,
            predicate=predicate,
        )

    @staticmethod
    def project(*fields: str) -> LogicalProjectionOperator:
        """Constructs a LogicalProjectionOperator."""
        op_id = f"op_project_{uuid.uuid4().hex[:8]}"
        return LogicalProjectionOperator(
            operator_id=op_id,
            output_schema=tuple(fields),
            projected_fields=tuple(fields),
        )

    @staticmethod
    def limit(count: int, offset: int = 0, input_fields: Tuple[str, ...] = ()) -> LogicalLimitOperator:
        """Constructs a LogicalLimitOperator."""
        op_id = f"op_limit_{uuid.uuid4().hex[:8]}"
        return LogicalLimitOperator(
            operator_id=op_id,
            output_schema=input_fields,
            limit=count,
            offset=offset,
        )


class OperatorChainBuilder:
    """Helper for building linear operator plan node chains."""

    @staticmethod
    def build_chain(operators: List[LogicalOperator]) -> LogicalPlanNode:
        """
        Chains a list of operators bottom-up (first operator is leaf, last operator is root).
        """
        if not operators:
            raise ValueError("Operator list for build_chain cannot be empty.")

        curr_node = LogicalPlanNode(
            node_id=f"lnode_{uuid.uuid4().hex[:8]}",
            operator=operators[0],
            children=(),
        )

        for op in operators[1:]:
            curr_node = LogicalPlanNode(
                node_id=f"lnode_{uuid.uuid4().hex[:8]}",
                operator=op,
                children=(curr_node,),
            )

        return curr_node


class LogicalPlanBuilder:
    """
    Fluent immutable builder for constructing LogicalPlan objects.
    """

    def __init__(
        self,
        query_id: Optional[QueryId] = None,
        root_operator: Optional[LogicalOperator] = None,
    ) -> None:
        self._query_id = query_id or QueryId(f"qry_{uuid.uuid4().hex[:12]}")
        self._root_operator = root_operator or LogicalOperatorBuilder.lookup("sym_default", name="default")
        self._children: Tuple[LogicalPlanNode, ...] = ()
        self._rules_applied: Tuple[str, ...] = ()

    def with_query_id(self, query_id: QueryId) -> "LogicalPlanBuilder":
        """Returns a new builder with updated query_id."""
        b = self._copy()
        b._query_id = query_id
        return b

    def with_lookup(self, symbol_id_str: str, name: str = "") -> "LogicalPlanBuilder":
        """Returns a new builder setting a LogicalLookupOperator root."""
        b = self._copy()
        b._root_operator = LogicalOperatorBuilder.lookup(symbol_id_str, name=name)
        return b

    def with_filter(self, predicate: QueryPredicate) -> "LogicalPlanBuilder":
        """Returns a new builder wrapping the current root in a LogicalFilterOperator."""
        b = self._copy()
        curr_node = LogicalPlanNode(
            node_id=f"lnode_{uuid.uuid4().hex[:8]}",
            operator=b._root_operator,
            children=b._children,
        )
        b._root_operator = LogicalOperatorBuilder.filter_op(predicate, input_fields=b._root_operator.output_schema)
        b._children = (curr_node,)
        return b

    def with_projection(self, *fields: str) -> "LogicalPlanBuilder":
        """Returns a new builder wrapping the current root in a LogicalProjectionOperator."""
        b = self._copy()
        curr_node = LogicalPlanNode(
            node_id=f"lnode_{uuid.uuid4().hex[:8]}",
            operator=b._root_operator,
            children=b._children,
        )
        b._root_operator = LogicalOperatorBuilder.project(*fields)
        b._children = (curr_node,)
        return b

    def with_limit(self, count: int, offset: int = 0) -> "LogicalPlanBuilder":
        """Returns a new builder wrapping the current root in a LogicalLimitOperator."""
        b = self._copy()
        curr_node = LogicalPlanNode(
            node_id=f"lnode_{uuid.uuid4().hex[:8]}",
            operator=b._root_operator,
            children=b._children,
        )
        b._root_operator = LogicalOperatorBuilder.limit(count, offset, input_fields=b._root_operator.output_schema)
        b._children = (curr_node,)
        return b

    def build(self) -> LogicalPlan:
        """Builds and returns the immutable LogicalPlan instance."""
        root_node = LogicalPlanNode(
            node_id=f"lnode_root_{uuid.uuid4().hex[:8]}",
            operator=self._root_operator,
            children=self._children,
        )
        meta = LogicalPlanMetadata(
            node_count=root_node.calculate_node_count(),
            tree_depth=root_node.calculate_depth(),
            lowering_rules_applied=self._rules_applied,
        )
        return LogicalPlan(
            query_id=self._query_id,
            metadata=meta,
            root_node=root_node,
        )

    def _copy(self) -> "LogicalPlanBuilder":
        b = LogicalPlanBuilder(query_id=self._query_id, root_operator=self._root_operator)
        b._children = self._children
        b._rules_applied = self._rules_applied
        return b


__all__ = [
    "LogicalOperatorBuilder",
    "OperatorChainBuilder",
    "LogicalPlanBuilder",
]
