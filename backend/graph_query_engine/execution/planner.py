"""
Execution Planner Subsystem Orchestration Engine.

Consumes PhysicalPlan → Produces an execution-independent immutable ExecutionPlan.
Partitions physical trees into executable stages, builds DAG dependency graphs, and allocates runtime metadata.
"""

import uuid
from typing import Any, List, Optional, Tuple

from graph_query_engine.execution.builder import PipelineGraphBuilder
from graph_query_engine.execution.diagnostics import ExecutionPlannerDiagnostics
from graph_query_engine.execution.operators import (
    AggregationExecutionOperator,
    DeduplicationExecutionOperator,
    ExpandExecutionOperator,
    FilterExecutionOperator,
    HashJoinExecutionOperator,
    IndexLookupExecutionOperator,
    LimitExecutionOperator,
    MergeJoinExecutionOperator,
    NestedLoopExecutionOperator,
    ProjectionExecutionOperator,
    SequentialLookupExecutionOperator,
    SortingExecutionOperator,
)
from graph_query_engine.execution.plan import ExecutionMetadata, ExecutionPlan
from graph_query_engine.execution.stage import ExecutionStage
from graph_query_engine.execution.validation import ExecutionPlanValidator
from graph_query_engine.physical.operators import (
    AggregationExecutionPhysicalOperator,
    BidirectionalExpandPhysicalOperator,
    BreadthExpandPhysicalOperator,
    DeduplicationExecutionPhysicalOperator,
    DepthExpandPhysicalOperator,
    FilterPushdownPhysicalOperator,
    HashJoinPhysicalOperator,
    IndexLookupPhysicalOperator,
    LimitExecutionPhysicalOperator,
    MergeJoinPhysicalOperator,
    NestedLoopJoinPhysicalOperator,
    PhysicalOperator,
    ProjectionPushdownPhysicalOperator,
    SequentialLookupPhysicalOperator,
    SortingExecutionPhysicalOperator,
)
from graph_query_engine.physical.plan import PhysicalPlan, PhysicalPlanNode


class ExecutionPlanner:
    """
    Main Execution Planner Orchestrator.

    Converts PhysicalPlan → ExecutionPlan.
    Decomposes operator trees into pipeline stages with explicit dependency graphs.
    Does NOT run graph traversals, does NOT execute queries, does NOT access GraphView.
    """

    def __init__(self) -> None:
        pass

    def create_execution_plan(
        self,
        physical_plan: PhysicalPlan,
    ) -> ExecutionPlan:
        """
        Transforms a PhysicalPlan into an immutable ExecutionPlan.
        """
        diagnostics = ExecutionPlannerDiagnostics()
        diagnostics.record_item(
            stage="ExecutionPlanning",
            message=f"Starting execution stage decomposition for PhysicalPlan '{physical_plan.plan_id}'",
        )

        stages: List[ExecutionStage] = []
        self._decompose_node(physical_plan.root_node, stages, parent_stage_id=None, diagnostics=diagnostics)

        # Reverse to get bottom-up execution order (leaf stage executes first)
        ordered_stages = tuple(reversed(stages))

        dag, pipeline = PipelineGraphBuilder.build_dag(list(ordered_stages))
        meta = ExecutionMetadata()

        preliminary_plan = ExecutionPlan(
            physical_plan_id=physical_plan.plan_id,
            query_id=physical_plan.query_id,
            metadata=meta,
            stages=ordered_stages,
            dependency_graph=dag,
            pipeline=pipeline,
            estimated_runtime_ms=physical_plan.total_cost_estimate.estimated_total_cost * 0.1,
            diagnostics=diagnostics.get_items(),
        )

        val_report = ExecutionPlanValidator.validate(preliminary_plan)
        if not val_report.is_valid:
            err_msg = "; ".join(v.message for v in val_report.violations if v.severity == "ERROR")
            diagnostics.record_item(stage="ExecutionValidation", message=err_msg, severity="WARNING")

        return ExecutionPlan(
            execution_plan_id=preliminary_plan.execution_plan_id,
            physical_plan_id=preliminary_plan.physical_plan_id,
            query_id=preliminary_plan.query_id,
            version=preliminary_plan.version,
            metadata=preliminary_plan.metadata,
            stages=ordered_stages,
            dependency_graph=dag,
            pipeline=pipeline,
            estimated_runtime_ms=preliminary_plan.estimated_runtime_ms,
            diagnostics=diagnostics.get_items(),
        )

    def _decompose_node(
        self,
        node: PhysicalPlanNode,
        stages: List[ExecutionStage],
        parent_stage_id: Optional[str],
        diagnostics: ExecutionPlannerDiagnostics,
    ) -> str:
        # Recursively process children first to establish dependency stage IDs
        child_stage_ids: List[str] = []
        for child in node.children:
            cid = self._decompose_node(child, stages, parent_stage_id=None, diagnostics=diagnostics)
            child_stage_ids.append(cid)

        dependencies = tuple(child_stage_ids)
        stage_id = f"stage_{uuid.uuid4().hex[:8]}"

        pop = node.operator
        eop = self._convert_physical_operator(pop)

        stage_type = self._determine_stage_type(pop)
        stage_name = f"{stage_type.capitalize()}Stage"

        stage = ExecutionStage(
            stage_id=stage_id,
            stage_name=stage_name,
            stage_type=stage_type,
            operators=(eop,),
            dependencies=dependencies,
            estimated_stage_cost=pop.estimated_cost,
        )

        diagnostics.record_stage_creation(
            stage_id=stage_id,
            stage_type=stage_type,
            dependencies=dependencies,
            rationale=f"Constructed {stage_name} wrapping PhysicalOperator '{pop.operator_name}'",
        )

        stages.append(stage)
        return stage_id

    def _determine_stage_type(self, pop: PhysicalOperator) -> str:
        name = pop.operator_name
        if "LOOKUP" in name:
            return "LOOKUP"
        elif "FILTER" in name:
            return "FILTER"
        elif "EXPAND" in name:
            return "EXPANSION"
        elif "PROJECTION" in name:
            return "PROJECTION"
        elif "JOIN" in name:
            return "JOIN"
        elif "AGGREGATION" in name:
            return "AGGREGATION"
        elif "SORTING" in name:
            return "SORTING"
        elif "DEDUPLICATION" in name:
            return "DEDUPLICATION"
        elif "LIMIT" in name:
            return "LIMIT"
        return "GENERAL"

    def _convert_physical_operator(self, pop: PhysicalOperator) -> Any:
        op_id = f"eop_{pop.operator_id}"
        schema = pop.output_schema
        cost = pop.estimated_cost
        ref = pop.operator_id

        if isinstance(pop, IndexLookupPhysicalOperator):
            return IndexLookupExecutionOperator(
                execution_operator_id=op_id,
                output_schema=schema,
                physical_operator_ref=ref,
                estimated_cost=cost,
                index_name=pop.index_name,
            )
        elif isinstance(pop, SequentialLookupPhysicalOperator):
            return SequentialLookupExecutionOperator(
                execution_operator_id=op_id,
                output_schema=schema,
                physical_operator_ref=ref,
                estimated_cost=cost,
            )
        elif isinstance(pop, (BreadthExpandPhysicalOperator, DepthExpandPhysicalOperator, BidirectionalExpandPhysicalOperator)):
            algo = "BFS" if isinstance(pop, BreadthExpandPhysicalOperator) else ("DFS" if isinstance(pop, DepthExpandPhysicalOperator) else "BIDIRECTIONAL")
            return ExpandExecutionOperator(
                execution_operator_id=op_id,
                output_schema=schema,
                physical_operator_ref=ref,
                estimated_cost=cost,
                traversal_algorithm=algo,
            )
        elif isinstance(pop, FilterPushdownPhysicalOperator):
            return FilterExecutionOperator(
                execution_operator_id=op_id,
                output_schema=schema,
                physical_operator_ref=ref,
                estimated_cost=cost,
                predicate=pop.predicate,
            )
        elif isinstance(pop, ProjectionPushdownPhysicalOperator):
            return ProjectionExecutionOperator(
                execution_operator_id=op_id,
                output_schema=schema,
                physical_operator_ref=ref,
                estimated_cost=cost,
                projected_fields=pop.projected_fields,
            )
        elif isinstance(pop, HashJoinPhysicalOperator):
            return HashJoinExecutionOperator(
                execution_operator_id=op_id,
                output_schema=schema,
                physical_operator_ref=ref,
                estimated_cost=cost,
                join_type=pop.join_type,
            )
        elif isinstance(pop, NestedLoopJoinPhysicalOperator):
            return NestedLoopExecutionOperator(
                execution_operator_id=op_id,
                output_schema=schema,
                physical_operator_ref=ref,
                estimated_cost=cost,
                join_type=pop.join_type,
            )
        elif isinstance(pop, AggregationExecutionPhysicalOperator):
            return AggregationExecutionOperator(
                execution_operator_id=op_id,
                output_schema=schema,
                physical_operator_ref=ref,
                estimated_cost=cost,
                function_name=pop.function_name,
                result_alias=pop.result_alias,
            )
        elif isinstance(pop, SortingExecutionPhysicalOperator):
            return SortingExecutionOperator(
                execution_operator_id=op_id,
                output_schema=schema,
                physical_operator_ref=ref,
                estimated_cost=cost,
                field_name=pop.field_name,
                ascending=pop.ascending,
            )
        elif isinstance(pop, DeduplicationExecutionPhysicalOperator):
            return DeduplicationExecutionOperator(
                execution_operator_id=op_id,
                output_schema=schema,
                physical_operator_ref=ref,
                estimated_cost=cost,
                distinct_fields=pop.distinct_fields,
            )
        elif isinstance(pop, LimitExecutionPhysicalOperator):
            return LimitExecutionOperator(
                execution_operator_id=op_id,
                output_schema=schema,
                physical_operator_ref=ref,
                estimated_cost=cost,
                limit=pop.limit,
                offset=pop.offset,
            )

        return SequentialLookupExecutionOperator(
            execution_operator_id=op_id,
            output_schema=schema,
            physical_operator_ref=ref,
            estimated_cost=cost,
        )


__all__ = ["ExecutionPlanner"]
