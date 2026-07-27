"""
Fluent Immutable Physical Plan Builders.

Constructs PhysicalPlan objects step-by-step without side-effects or execution.
100% Immutable builder pattern - every method call returns a new builder/plan object.
"""

import uuid
from typing import Any, List, Optional, Tuple

from graph_query_engine.cost import CostEstimate
from graph_query_engine.physical.operators import (
    BreadthExpandPhysicalOperator,
    FilterPushdownPhysicalOperator,
    IndexLookupPhysicalOperator,
    LimitExecutionPhysicalOperator,
    PhysicalOperator,
    ProjectionPushdownPhysicalOperator,
)
from graph_query_engine.physical.plan import (
    PhysicalPlan,
    PhysicalPlanMetadata,
    PhysicalPlanNode,
)
from graph_query_engine.types import QueryId


class PhysicalOperatorBuilder:
    """Helper builder for constructing individual PhysicalOperator nodes."""

    @staticmethod
    def index_lookup(symbol_id_str: str, index_name: str = "PRIMARY_INDEX") -> IndexLookupPhysicalOperator:
        """Constructs an IndexLookupPhysicalOperator."""
        op_id = f"op_idx_{uuid.uuid4().hex[:8]}"
        return IndexLookupPhysicalOperator(
            operator_id=op_id,
            output_schema=("id", "name", "kind"),
            index_name=index_name,
        )

    @staticmethod
    def breadth_expand() -> BreadthExpandPhysicalOperator:
        """Constructs a BreadthExpandPhysicalOperator."""
        op_id = f"op_bfs_{uuid.uuid4().hex[:8]}"
        return BreadthExpandPhysicalOperator(
            operator_id=op_id,
            output_schema=("source_id", "target_id", "relationship_type"),
        )

    @staticmethod
    def filter_pushdown(input_fields: Tuple[str, ...] = ()) -> FilterPushdownPhysicalOperator:
        """Constructs a FilterPushdownPhysicalOperator."""
        op_id = f"op_pf_{uuid.uuid4().hex[:8]}"
        return FilterPushdownPhysicalOperator(
            operator_id=op_id,
            output_schema=input_fields,
        )

    @staticmethod
    def projection_pushdown(*fields: str) -> ProjectionPushdownPhysicalOperator:
        """Constructs a ProjectionPushdownPhysicalOperator."""
        op_id = f"op_pp_{uuid.uuid4().hex[:8]}"
        return ProjectionPushdownPhysicalOperator(
            operator_id=op_id,
            output_schema=tuple(fields),
            projected_fields=tuple(fields),
        )

    @staticmethod
    def limit_execution(count: int, offset: int = 0, input_fields: Tuple[str, ...] = ()) -> LimitExecutionPhysicalOperator:
        """Constructs a LimitExecutionPhysicalOperator."""
        op_id = f"op_plimit_{uuid.uuid4().hex[:8]}"
        return LimitExecutionPhysicalOperator(
            operator_id=op_id,
            output_schema=input_fields,
            limit=count,
            offset=offset,
        )


class ExecutionPipelineBuilder:
    """Helper for chaining linear physical execution operator node pipelines."""

    @staticmethod
    def build_pipeline(operators: List[PhysicalOperator]) -> PhysicalPlanNode:
        """Chains a list of physical operators bottom-up into a PhysicalPlanNode tree."""
        if not operators:
            raise ValueError("Operator list for build_pipeline cannot be empty.")

        curr_node = PhysicalPlanNode(
            node_id=f"pnode_{uuid.uuid4().hex[:8]}",
            operator=operators[0],
            children=(),
        )

        for op in operators[1:]:
            curr_node = PhysicalPlanNode(
                node_id=f"pnode_{uuid.uuid4().hex[:8]}",
                operator=op,
                children=(curr_node,),
            )

        return curr_node


class PhysicalPlanBuilder:
    """
    Fluent immutable builder for constructing PhysicalPlan objects.
    """

    def __init__(
        self,
        logical_plan_id: str = "lplan_default",
        query_id: Optional[QueryId] = None,
        root_operator: Optional[PhysicalOperator] = None,
    ) -> None:
        self._logical_plan_id = logical_plan_id
        self._query_id = query_id or QueryId(f"qry_{uuid.uuid4().hex[:12]}")
        self._root_operator = root_operator or PhysicalOperatorBuilder.index_lookup("sym_default")
        self._children: Tuple[PhysicalPlanNode, ...] = ()
        self._rationales: Tuple[str, ...] = ()
        self._total_cost = CostEstimate()

    def with_logical_plan_id(self, lplan_id: str) -> "PhysicalPlanBuilder":
        """Returns a new builder with updated logical_plan_id."""
        b = self._copy()
        b._logical_plan_id = lplan_id
        return b

    def with_index_lookup(self, symbol_id_str: str) -> "PhysicalPlanBuilder":
        """Returns a new builder setting IndexLookupPhysicalOperator root."""
        b = self._copy()
        b._root_operator = PhysicalOperatorBuilder.index_lookup(symbol_id_str)
        return b

    def with_filter_pushdown(self) -> "PhysicalPlanBuilder":
        """Returns a new builder wrapping root in a FilterPushdownPhysicalOperator."""
        b = self._copy()
        curr_node = PhysicalPlanNode(
            node_id=f"pnode_{uuid.uuid4().hex[:8]}",
            operator=b._root_operator,
            children=b._children,
        )
        b._root_operator = PhysicalOperatorBuilder.filter_pushdown(input_fields=b._root_operator.output_schema)
        b._children = (curr_node,)
        return b

    def build(self) -> PhysicalPlan:
        """Builds and returns the immutable PhysicalPlan instance."""
        root_node = PhysicalPlanNode(
            node_id=f"pnode_root_{uuid.uuid4().hex[:8]}",
            operator=self._root_operator,
            children=self._children,
        )
        meta = PhysicalPlanMetadata(
            node_count=root_node.calculate_node_count(),
            tree_depth=root_node.calculate_depth(),
            execution_strategy_name="PHYSICAL_INDEX_LOOKUP_STRATEGY",
            strategy_rationales=self._rationales,
        )
        return PhysicalPlan(
            logical_plan_id=self._logical_plan_id,
            query_id=self._query_id,
            metadata=meta,
            total_cost_estimate=self._total_cost,
            root_node=root_node,
        )

    def _copy(self) -> "PhysicalPlanBuilder":
        b = PhysicalPlanBuilder(
            logical_plan_id=self._logical_plan_id,
            query_id=self._query_id,
            root_operator=self._root_operator,
        )
        b._children = self._children
        b._rationales = self._rationales
        b._total_cost = self._total_cost
        return b


__all__ = [
    "PhysicalOperatorBuilder",
    "ExecutionPipelineBuilder",
    "PhysicalPlanBuilder",
]
