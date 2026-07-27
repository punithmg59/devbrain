"""
Fluent Immutable Execution Plan Builders.

Constructs ExecutionPlan objects step-by-step without side-effects or runtime execution.
100% Immutable builder pattern - every method call returns a new builder/plan object.
"""

import uuid
from typing import Any, List, Optional, Tuple

from graph_query_engine.execution.operators import (
    ExpandExecutionOperator,
    FilterExecutionOperator,
    IndexLookupExecutionOperator,
    LimitExecutionOperator,
    ProjectionExecutionOperator,
)
from graph_query_engine.execution.pipeline import ExecutionPipeline, StageDependencyGraph
from graph_query_engine.execution.plan import ExecutionMetadata, ExecutionPlan
from graph_query_engine.execution.stage import ExecutionStage
from graph_query_engine.types import QueryId


class ExecutionStageBuilder:
    """Helper builder for creating individual ExecutionStage objects."""

    @staticmethod
    def lookup_stage(symbol_id_str: str, stage_id: str = "stage_lookup_1") -> ExecutionStage:
        """Constructs a lookup ExecutionStage."""
        op = IndexLookupExecutionOperator(
            execution_operator_id=f"eop_idx_{uuid.uuid4().hex[:8]}",
            output_schema=("id", "name", "kind"),
            index_name="PRIMARY_INDEX",
        )
        return ExecutionStage(
            stage_id=stage_id,
            stage_name="LookupStage",
            stage_type="LOOKUP",
            operators=(op,),
            dependencies=(),
        )

    @staticmethod
    def filter_stage(stage_id: str = "stage_filter_1", dependencies: Tuple[str, ...] = ()) -> ExecutionStage:
        """Constructs a filter ExecutionStage."""
        op = FilterExecutionOperator(
            execution_operator_id=f"eop_flt_{uuid.uuid4().hex[:8]}",
            output_schema=("id", "name", "kind"),
        )
        return ExecutionStage(
            stage_id=stage_id,
            stage_name="FilterStage",
            stage_type="FILTER",
            operators=(op,),
            dependencies=dependencies,
        )


class PipelineGraphBuilder:
    """Helper for constructing stage dependency DAGs and pipeline order."""

    @staticmethod
    def build_dag(stages: List[ExecutionStage]) -> Tuple[StageDependencyGraph, ExecutionPipeline]:
        """Builds topological order and StageDependencyGraph for a list of stages."""
        stage_ids = tuple(s.stage_id for s in stages)
        dep_edges = {s.stage_id: s.dependencies for s in stages}
        topo_order = tuple(s.stage_id for s in stages)  # Preserves stage sequence order

        dag = StageDependencyGraph(
            stage_ids=stage_ids,
            dependency_edges=dep_edges,
            topological_order=topo_order,
        )

        pipeline = ExecutionPipeline(
            pipeline_id=f"pipe_{uuid.uuid4().hex[:8]}",
            stages=tuple(stages),
        )

        return dag, pipeline


class ExecutionPlanBuilder:
    """
    Fluent immutable builder for constructing ExecutionPlan objects.
    """

    def __init__(
        self,
        physical_plan_id: str = "pplan_default",
        query_id: Optional[QueryId] = None,
    ) -> None:
        self._physical_plan_id = physical_plan_id
        self._query_id = query_id or QueryId(f"qry_{uuid.uuid4().hex[:12]}")
        self._stages: List[ExecutionStage] = [ExecutionStageBuilder.lookup_stage("sym_default")]
        self._timeout_ms: int = 30_000

    def with_physical_plan_id(self, pplan_id: str) -> "ExecutionPlanBuilder":
        """Returns a new builder with updated physical_plan_id."""
        b = self._copy()
        b._physical_plan_id = pplan_id
        return b

    def with_stage(self, stage: ExecutionStage) -> "ExecutionPlanBuilder":
        """Returns a new builder appending an ExecutionStage."""
        b = self._copy()
        b._stages.append(stage)
        return b

    def with_timeout_ms(self, timeout_ms: int) -> "ExecutionPlanBuilder":
        """Returns a new builder with updated execution timeout."""
        b = self._copy()
        b._timeout_ms = timeout_ms
        return b

    def build(self) -> ExecutionPlan:
        """Builds and returns the immutable ExecutionPlan instance."""
        dag, pipeline = PipelineGraphBuilder.build_dag(self._stages)
        meta = ExecutionMetadata(timeout_ms=self._timeout_ms)

        return ExecutionPlan(
            physical_plan_id=self._physical_plan_id,
            query_id=self._query_id,
            metadata=meta,
            stages=tuple(self._stages),
            dependency_graph=dag,
            pipeline=pipeline,
        )

    def _copy(self) -> "ExecutionPlanBuilder":
        b = ExecutionPlanBuilder(
            physical_plan_id=self._physical_plan_id,
            query_id=self._query_id,
        )
        b._stages = list(self._stages)
        b._timeout_ms = self._timeout_ms
        return b


__all__ = [
    "ExecutionStageBuilder",
    "PipelineGraphBuilder",
    "ExecutionPlanBuilder",
]
