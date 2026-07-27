"""
Physical Execution Strategy Selectors.

Chooses concrete physical execution strategies based on CostReport estimates and operator characteristics.
"""

from typing import Optional, Tuple
from graph_query_engine.cost.estimate import CostEstimate, CostReport, OperatorCostBreakdown
from graph_query_engine.logical.operators import (
    LogicalExpandOperator,
    LogicalFilterOperator,
    LogicalJoinOperator,
    LogicalLookupOperator,
    LogicalOperator,
    LogicalProjectionOperator,
)
from graph_query_engine.physical.diagnostics import PhysicalPlannerDiagnostics
from graph_query_engine.physical.operators import (
    BidirectionalExpandPhysicalOperator,
    BreadthExpandPhysicalOperator,
    DepthExpandPhysicalOperator,
    FilterPushdownPhysicalOperator,
    HashJoinPhysicalOperator,
    IndexLookupPhysicalOperator,
    MergeJoinPhysicalOperator,
    NestedLoopJoinPhysicalOperator,
    PhysicalOperator,
    ProjectionPushdownPhysicalOperator,
    SequentialLookupPhysicalOperator,
)


class LookupStrategySelector:
    """Selects IndexLookup vs SequentialLookup execution strategy."""

    @classmethod
    def select_strategy(
        cls,
        logical_op: LogicalLookupOperator,
        cost_breakdown: Optional[OperatorCostBreakdown],
        diagnostics: PhysicalPlannerDiagnostics,
    ) -> PhysicalOperator:
        """Selects physical lookup strategy."""
        op_id = logical_op.operator_id
        ref = logical_op.target_reference

        # If reference contains an identifier/symbol_id, select IndexLookup
        if ref and (ref.identifier or getattr(ref, "symbol_id", None)):
            selected = "INDEX_LOOKUP"
            rejected = ("SEQUENTIAL_SCAN",)
            rationale = "Available primary/symbol index lookup strategy selected for point query."
            diagnostics.record_choice(op_id, selected, rejected, rationale)
            return IndexLookupPhysicalOperator(
                operator_id=f"phys_{op_id}",
                output_schema=logical_op.output_schema,
                index_name="PRIMARY_INDEX",
                target_reference=ref,
            )

        selected = "SEQUENTIAL_SCAN"
        rejected = ("INDEX_LOOKUP",)
        rationale = "Sequential lookup selected due to unindexed search reference."
        diagnostics.record_choice(op_id, selected, rejected, rationale)
        return SequentialLookupPhysicalOperator(
            operator_id=f"phys_{op_id}",
            output_schema=logical_op.output_schema,
            target_reference=ref,
        )


class ExpandStrategySelector:
    """Selects BreadthExpand vs DepthExpand vs BidirectionalExpand strategy."""

    @classmethod
    def select_strategy(
        cls,
        logical_op: LogicalExpandOperator,
        cost_breakdown: Optional[OperatorCostBreakdown],
        diagnostics: PhysicalPlannerDiagnostics,
    ) -> PhysicalOperator:
        """Selects physical expansion strategy."""
        op_id = logical_op.operator_id
        req = logical_op.traversal_request
        depth = req.constraints.max_depth if req and req.constraints else 1

        if depth > 3:
            selected = "DEPTH_EXPAND"
            rejected = ("BREADTH_EXPAND", "BIDIRECTIONAL_EXPAND")
            rationale = f"Depth-First Search (DFS) selected for deep traversal (max_depth={depth})."
            diagnostics.record_choice(op_id, selected, rejected, rationale)
            return DepthExpandPhysicalOperator(
                operator_id=f"phys_{op_id}",
                output_schema=logical_op.output_schema,
                traversal_request=req,
            )

        selected = "BREADTH_EXPAND"
        rejected = ("DEPTH_EXPAND", "BIDIRECTIONAL_EXPAND")
        rationale = f"Breadth-First Search (BFS) selected for shallow expansion (max_depth={depth})."
        diagnostics.record_choice(op_id, selected, rejected, rationale)
        return BreadthExpandPhysicalOperator(
            operator_id=f"phys_{op_id}",
            output_schema=logical_op.output_schema,
            traversal_request=req,
        )


class JoinStrategySelector:
    """Selects HashJoin vs NestedLoopJoin vs MergeJoin strategy."""

    @classmethod
    def select_strategy(
        cls,
        logical_op: LogicalJoinOperator,
        cost_breakdown: Optional[OperatorCostBreakdown],
        diagnostics: PhysicalPlannerDiagnostics,
    ) -> PhysicalOperator:
        """Selects physical join strategy based on estimated cardinality."""
        op_id = logical_op.operator_id
        cardinality = cost_breakdown.estimate.estimated_cardinality if cost_breakdown else 100.0

        if cardinality < 20.0:
            selected = "NESTED_LOOP_JOIN"
            rejected = ("HASH_JOIN", "MERGE_JOIN")
            rationale = f"Nested loop join selected for small estimated cardinality ({cardinality:.1f})."
            diagnostics.record_choice(op_id, selected, rejected, rationale)
            return NestedLoopJoinPhysicalOperator(
                operator_id=f"phys_{op_id}",
                output_schema=logical_op.output_schema,
                join_type=logical_op.join_type,
                on_predicate=logical_op.on_predicate,
            )

        selected = "HASH_JOIN"
        rejected = ("NESTED_LOOP_JOIN", "MERGE_JOIN")
        rationale = f"Hash join selected for medium/large estimated cardinality ({cardinality:.1f})."
        diagnostics.record_choice(op_id, selected, rejected, rationale)
        return HashJoinPhysicalOperator(
            operator_id=f"phys_{op_id}",
            output_schema=logical_op.output_schema,
            join_type=logical_op.join_type,
            on_predicate=logical_op.on_predicate,
        )


class PushdownStrategySelector:
    """Selects FilterPushdown and ProjectionPushdown physical strategies."""

    @classmethod
    def select_filter(
        cls,
        logical_op: LogicalFilterOperator,
        cost_breakdown: Optional[OperatorCostBreakdown],
        diagnostics: PhysicalPlannerDiagnostics,
    ) -> PhysicalOperator:
        op_id = logical_op.operator_id
        diagnostics.record_choice(
            op_id,
            "FILTER_PUSHDOWN",
            ("POST_SCAN_FILTER",),
            "Pushed down filter predicate evaluation to scan layer.",
        )
        return FilterPushdownPhysicalOperator(
            operator_id=f"phys_{op_id}",
            output_schema=logical_op.output_schema,
            predicate=logical_op.predicate,
        )

    @classmethod
    def select_projection(
        cls,
        logical_op: LogicalProjectionOperator,
        cost_breakdown: Optional[OperatorCostBreakdown],
        diagnostics: PhysicalPlannerDiagnostics,
    ) -> PhysicalOperator:
        op_id = logical_op.operator_id
        diagnostics.record_choice(
            op_id,
            "PROJECTION_PUSHDOWN",
            ("FULL_SCHEMA_PASS",),
            "Pushed down field projection to cut intermediate tuple width.",
        )
        return ProjectionPushdownPhysicalOperator(
            operator_id=f"phys_{op_id}",
            output_schema=logical_op.output_schema,
            projected_fields=logical_op.projected_fields,
        )


__all__ = [
    "LookupStrategySelector",
    "ExpandStrategySelector",
    "JoinStrategySelector",
    "PushdownStrategySelector",
]
