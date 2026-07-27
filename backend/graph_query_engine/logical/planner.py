"""
Logical Planner Orchestration Subsystem.

The LogicalPlanner consumes a validated EngineeringQuery AST and produces
an execution-independent, 100% immutable LogicalPlan.
"""

from typing import Optional, Tuple
from graph_query_engine.logical.diagnostics import LogicalPlannerDiagnostics
from graph_query_engine.logical.errors import LogicalValidationError
from graph_query_engine.logical.lowering import ASTLoweringPipeline
from graph_query_engine.logical.plan import (
    LogicalPlan,
    LogicalPlanMetadata,
    LogicalPlanNode,
)
from graph_query_engine.logical.validation import LogicalPlanValidator
from graph_query_engine.planner import PlannerLifecycle, PlannerState
from graph_query_engine.query import EngineeringQuery, QueryValidator


class LogicalPlanner:
    """
    Main Logical Planner Orchestrator.

    Consumes Query AST → Produces LogicalPlan.
    Does NOT select physical indexes, estimate costs, touch GraphView, or execute graph queries.
    """

    def __init__(self, pipeline: Optional[ASTLoweringPipeline] = None) -> None:
        self.pipeline = pipeline or ASTLoweringPipeline()

    def create_plan(
        self,
        query: EngineeringQuery,
        lifecycle: Optional[PlannerLifecycle] = None,
    ) -> LogicalPlan:
        """
        Orchestrates AST validation, lowering rules application, logical plan validation,
        and returns the canonical LogicalPlan.
        """
        lc = lifecycle or PlannerLifecycle()
        diagnostics = LogicalPlannerDiagnostics()

        # 1. Transition state to VALIDATING
        if lc.current_state == PlannerState.CREATED:
            lc.transition_to(PlannerState.INITIALIZED)
        lc.transition_to(PlannerState.VALIDATING)

        diagnostics.record_item(
            stage="QueryValidation",
            message=f"Validating input EngineeringQuery '{query.query_id}'",
        )

        query_report = QueryValidator.validate(query)
        if not query_report.is_valid:
            err_msg = "; ".join(v.message for v in query_report.violations if v.severity == "ERROR")
            diagnostics.record_item(stage="QueryValidation", message=err_msg, severity="ERROR")
            lc.transition_to(PlannerState.FAILED)
            raise LogicalValidationError(
                message=f"EngineeringQuery input validation failed: {err_msg}",
                stage="QueryValidation",
            )

        # 2. Transition state to PLANNING (AST Lowering)
        lc.transition_to(PlannerState.PLANNING)
        diagnostics.record_item(
            stage="ASTLowering",
            message="Invoking ASTLoweringPipeline transformation",
        )

        root_plan_node, context = self.pipeline.lower_query(query)

        for rule in context.rules_applied:
            diagnostics.record_item(
                stage="ASTLowering",
                message=f"Applied AST lowering rule '{rule}'",
            )

        # 3. Build preliminary plan and validate logical tree structure
        meta = LogicalPlanMetadata(
            node_count=root_plan_node.calculate_node_count(),
            tree_depth=root_plan_node.calculate_depth(),
            lowering_rules_applied=tuple(context.rules_applied),
        )

        preliminary_plan = LogicalPlan(
            query_id=query.query_id,
            metadata=meta,
            root_node=root_plan_node,
            diagnostics=diagnostics.get_items(),
        )

        val_report = LogicalPlanValidator.validate(preliminary_plan)
        if not val_report.is_valid:
            err_msg = "; ".join(v.message for v in val_report.violations if v.severity == "ERROR")
            diagnostics.record_item(stage="LogicalValidation", message=err_msg, severity="ERROR")
            lc.transition_to(PlannerState.FAILED)
            raise LogicalValidationError(
                message=f"LogicalPlan validation failed: {err_msg}",
                stage="LogicalValidation",
            )

        # 4. Transition state to COMPLETED (or BUILDING_PLAN)
        if lc.current_state == PlannerState.PLANNING:
            lc.transition_to(PlannerState.BUILDING_PLAN)
            lc.transition_to(PlannerState.COMPLETED)

        # Final immutable plan with full diagnostics
        return LogicalPlan(
            plan_id=preliminary_plan.plan_id,
            query_id=query.query_id,
            version=preliminary_plan.version,
            metadata=meta,
            statistics=preliminary_plan.statistics,
            root_node=root_plan_node,
            diagnostics=diagnostics.get_items(),
        )


__all__ = ["LogicalPlanner"]
