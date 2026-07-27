"""
Physical Planner Subsystem Orchestration Engine.

Consumes LogicalPlan + CostReport → Produces an execution-independent immutable PhysicalPlan.
Decides physical algorithms, index strategy, expansion strategy, and pushdown operations without execution.
"""

import uuid
from typing import Dict, Optional, Tuple

from graph_query_engine.cost.estimate import CostReport, OperatorCostBreakdown
from graph_query_engine.logical.operators import (
    LogicalAggregateOperator,
    LogicalDeduplicationOperator,
    LogicalExpandOperator,
    LogicalFilterOperator,
    LogicalGroupingOperator,
    LogicalJoinOperator,
    LogicalLimitOperator,
    LogicalLookupOperator,
    LogicalOperator,
    LogicalProjectionOperator,
    LogicalSortingOperator,
)
from graph_query_engine.logical.plan import LogicalPlan, LogicalPlanNode
from graph_query_engine.physical.diagnostics import PhysicalPlannerDiagnostics
from graph_query_engine.physical.operators import (
    AggregationExecutionPhysicalOperator,
    DeduplicationExecutionPhysicalOperator,
    LimitExecutionPhysicalOperator,
    PhysicalOperator,
    SortingExecutionPhysicalOperator,
)
from graph_query_engine.physical.plan import (
    PhysicalPlan,
    PhysicalPlanMetadata,
    PhysicalPlanNode,
)
from graph_query_engine.physical.strategy import (
    ExpandStrategySelector,
    JoinStrategySelector,
    LookupStrategySelector,
    PushdownStrategySelector,
)
from graph_query_engine.physical.validation import PhysicalPlanValidator


class PhysicalPlanner:
    """
    Main Physical Planner Orchestrator.

    Converts LogicalPlan + CostReport → PhysicalPlan.
    Does NOT run traversals, does NOT execute queries, does NOT access GraphView.
    """

    def __init__(self) -> None:
        pass

    def create_physical_plan(
        self,
        logical_plan: LogicalPlan,
        cost_report: CostReport,
    ) -> PhysicalPlan:
        """
        Transforms a LogicalPlan into an immutable PhysicalPlan using cost metrics.
        """
        diagnostics = PhysicalPlannerDiagnostics()
        diagnostics.record_item(
            stage="PhysicalPlanning",
            message=f"Starting physical strategy selection for LogicalPlan '{logical_plan.plan_id}'",
        )

        cost_map: Dict[str, OperatorCostBreakdown] = {
            b.operator_id: b for b in cost_report.operator_costs
        }

        root_pnode = self._convert_node(logical_plan.root_node, cost_map, diagnostics)

        meta = PhysicalPlanMetadata(
            node_count=root_pnode.calculate_node_count(),
            tree_depth=root_pnode.calculate_depth(),
            execution_strategy_name="PHYSICAL_COST_OPTIMIZED_STRATEGY",
            strategy_rationales=tuple(item.rationale for item in diagnostics.get_items() if item.rationale),
        )

        preliminary_plan = PhysicalPlan(
            logical_plan_id=logical_plan.plan_id,
            query_id=logical_plan.query_id,
            metadata=meta,
            total_cost_estimate=cost_report.total_cost_estimate,
            root_node=root_pnode,
            diagnostics=diagnostics.get_items(),
        )

        val_report = PhysicalPlanValidator.validate(preliminary_plan)
        if not val_report.is_valid:
            err_msg = "; ".join(v.message for v in val_report.violations if v.severity == "ERROR")
            diagnostics.record_item(stage="PhysicalValidation", message=err_msg, severity="WARNING")

        return PhysicalPlan(
            plan_id=preliminary_plan.plan_id,
            logical_plan_id=preliminary_plan.logical_plan_id,
            query_id=preliminary_plan.query_id,
            version=preliminary_plan.version,
            metadata=meta,
            total_cost_estimate=preliminary_plan.total_cost_estimate,
            root_node=root_pnode,
            diagnostics=diagnostics.get_items(),
        )

    def _convert_node(
        self,
        logical_node: LogicalPlanNode,
        cost_map: Dict[str, OperatorCostBreakdown],
        diagnostics: PhysicalPlannerDiagnostics,
    ) -> PhysicalPlanNode:
        # Recursively convert child input nodes
        child_pnodes: List[PhysicalPlanNode] = []
        for child in logical_node.children:
            child_pnodes.append(self._convert_node(child, cost_map, diagnostics))

        children_tuple = tuple(child_pnodes)
        log_op = logical_node.operator
        cost_bd = cost_map.get(log_op.operator_id)

        phys_op = self._select_physical_operator(log_op, cost_bd, diagnostics)

        return PhysicalPlanNode(
            node_id=f"pnode_{uuid.uuid4().hex[:8]}",
            operator=phys_op,
            children=children_tuple,
        )

    def _select_physical_operator(
        self,
        log_op: LogicalOperator,
        cost_bd: Optional[OperatorCostBreakdown],
        diagnostics: PhysicalPlannerDiagnostics,
    ) -> PhysicalOperator:
        op_id = log_op.operator_id
        est_cost = cost_bd.estimate if cost_bd else None

        if isinstance(log_op, LogicalLookupOperator):
            op = LookupStrategySelector.select_strategy(log_op, cost_bd, diagnostics)
        elif isinstance(log_op, LogicalExpandOperator):
            op = ExpandStrategySelector.select_strategy(log_op, cost_bd, diagnostics)
        elif isinstance(log_op, LogicalFilterOperator):
            op = PushdownStrategySelector.select_filter(log_op, cost_bd, diagnostics)
        elif isinstance(log_op, LogicalProjectionOperator):
            op = PushdownStrategySelector.select_projection(log_op, cost_bd, diagnostics)
        elif isinstance(log_op, LogicalJoinOperator):
            op = JoinStrategySelector.select_strategy(log_op, cost_bd, diagnostics)
        elif isinstance(log_op, LogicalAggregateOperator):
            op = AggregationExecutionPhysicalOperator(
                operator_id=f"phys_{op_id}",
                output_schema=log_op.output_schema,
                function_name=log_op.function_name,
                result_alias=log_op.result_alias,
            )
        elif isinstance(log_op, LogicalSortingOperator):
            op = SortingExecutionPhysicalOperator(
                operator_id=f"phys_{op_id}",
                output_schema=log_op.output_schema,
                field_name=log_op.field_name,
                ascending=log_op.ascending,
            )
        elif isinstance(log_op, LogicalDeduplicationOperator):
            op = DeduplicationExecutionPhysicalOperator(
                operator_id=f"phys_{op_id}",
                output_schema=log_op.output_schema,
                distinct_fields=log_op.distinct_fields,
            )
        elif isinstance(log_op, LogicalLimitOperator):
            op = LimitExecutionPhysicalOperator(
                operator_id=f"phys_{op_id}",
                output_schema=log_op.output_schema,
                limit=log_op.limit,
                offset=log_op.offset,
            )
        else:
            op = PhysicalOperator(
                operator_id=f"phys_{op_id}",
                operator_name=f"GENERIC_PHYSICAL_{log_op.operator_name}",
                output_schema=log_op.output_schema,
            )

        if est_cost:
            # Model construct with updated estimated cost
            op = type(op).model_construct(
                **{**op.model_dump(), "estimated_cost": est_cost}
            )

        return op


__all__ = ["PhysicalPlanner"]
