"""
Public Query API Executor.

Orchestrates the internal end-to-end Graph Query Engine pipeline:
Request Validation -> EngineeringQuery AST -> LogicalPlanner -> CostModel -> PhysicalPlanner ->
PlannerOptimizer -> ExecutionPlanner -> TraversalEngine -> Public QueryResult/Response.

Internal pipeline details remain strictly hidden from API callers.
"""

import time
from typing import Any, Dict, List, Optional

from graph_query_engine.api.context import QueryContext
from graph_query_engine.api.errors import QueryErrorCode, QueryErrorDetail
from graph_query_engine.api.exceptions import (
    QueryExecutionException,
    QueryValidationException,
)
from graph_query_engine.api.request import QueryRequest
from graph_query_engine.api.response import QueryResponse, ResponseStatus
from graph_query_engine.api.result import QueryDiagnostics, QueryResult, QueryStatistics
from graph_query_engine.api.validation import QueryValidation
from graph_query_engine.cost import CostEstimator
from graph_query_engine.execution import ExecutionPlanner
from graph_query_engine.logical import LogicalPlanner
from graph_query_engine.optimizer import PlannerOptimizer
from graph_query_engine.optimizer.contracts import PhysicalPlan as OptPhysicalPlan
from graph_query_engine.physical import PhysicalPlanner
from graph_query_engine.query import EngineeringQuery, QueryBuilder
from graph_query_engine.traversal import TraversalEngine, TraversalLimits, TraversalResult


class QueryExecutor:
    """
    Production-grade end-to-end Query Executor orchestrator.
    """

    def __init__(
        self,
        logical_planner: Optional[LogicalPlanner] = None,
        cost_estimator: Optional[CostEstimator] = None,
        physical_planner: Optional[PhysicalPlanner] = None,
        planner_optimizer: Optional[PlannerOptimizer] = None,
        execution_planner: Optional[ExecutionPlanner] = None,
        traversal_engine: Optional[TraversalEngine] = None,
    ) -> None:
        self.logical_planner = logical_planner or LogicalPlanner()
        self.cost_estimator = cost_estimator or CostEstimator()
        self.physical_planner = physical_planner or PhysicalPlanner()
        self.planner_optimizer = planner_optimizer or PlannerOptimizer()
        self.execution_planner = execution_planner or ExecutionPlanner()
        self.traversal_engine = traversal_engine or TraversalEngine()

    def execute(
        self,
        request: QueryRequest,
        graph_view: Optional[Any] = None,
        index_layer: Optional[Any] = None,
    ) -> QueryResponse:
        """
        Executes a QueryRequest through the complete hidden internal pipeline.
        """
        start_time = time.perf_counter()
        planning_time_ms = 0.0
        optimization_time_ms = 0.0
        execution_time_ms = 0.0

        # 1. Validation phase
        val_report = QueryValidation.validate(request)
        if not val_report.is_valid:
            errors = [v.message for v in val_report.violations if v.severity == "ERROR"]
            err_msg = f"QueryRequest validation failed: {'; '.join(errors)}"
            err_detail = QueryErrorDetail(
                code=QueryErrorCode.VALIDATION_FAILED,
                message=err_msg,
                details={"violations": [v.model_dump() for v in val_report.violations]},
            )
            return QueryResponse(
                request_id=request.request_id,
                status=ResponseStatus.FAILED,
                error=err_detail,
                diagnostics=QueryDiagnostics(errors=errors),
            )

        try:
            # 2. Build EngineeringQuery AST
            eng_query = self._build_engineering_query(request)

            # 3. Logical Planning
            t_plan_start = time.perf_counter()
            logical_plan = self.logical_planner.create_plan(eng_query)
            planning_time_ms = (time.perf_counter() - t_plan_start) * 1000.0

            # 4. Cost Model Estimation & Physical Planning & Rule Optimization
            t_opt_start = time.perf_counter()
            cost_report = self.cost_estimator.estimate_plan_cost(logical_plan)

            physical_plan = self.physical_planner.create_physical_plan(
                logical_plan=logical_plan,
                cost_report=cost_report,
            )

            # Run rule-based physical optimizer pass
            opt_input = OptPhysicalPlan(
                operators=[
                    {
                        "type": "lookup",
                        "operator_name": physical_plan.root_node.operator.operator_name,
                        **physical_plan.root_node.operator.model_dump(mode="python"),
                    }
                ]
            )
            _ = self.planner_optimizer.optimize(opt_input)

            # Decompose into ExecutionPlan
            execution_plan = self.execution_planner.create_execution_plan(physical_plan)
            optimization_time_ms = (time.perf_counter() - t_opt_start) * 1000.0

            # 5. Traversal Engine Execution
            t_exec_start = time.perf_counter()
            limits = TraversalLimits(
                max_depth=request.context.depth_limit,
                max_nodes=request.context.max_nodes_limit,
                timeout_seconds=request.context.timeout_seconds,
            )

            traversal_result: Optional[TraversalResult] = None

            if graph_view is not None:
                op = request.operation.lower()
                start_nodes = [request.target] if request.target else ["root"]

                if op in ("find_paths", "find_shortest_path"):
                    target_node = request.parameters.get("destination") or request.parameters.get("target_node") or request.target
                    traversal_result = self.traversal_engine.execute_algorithm(
                        algorithm="shortest_path",
                        graph_view=graph_view,
                        start_nodes=start_nodes,
                        target_node=target_node,
                        index_layer=index_layer,
                        limits=limits,
                    )
                elif op in ("find_cycles", "detect_cycles"):
                    traversal_result = self.traversal_engine.execute_algorithm(
                        algorithm="cycle_detection",
                        graph_view=graph_view,
                        start_nodes=start_nodes,
                        index_layer=index_layer,
                        limits=limits,
                    )
                elif op in ("find_connected_components",):
                    traversal_result = self.traversal_engine.execute_algorithm(
                        algorithm="connected_components",
                        graph_view=graph_view,
                        start_nodes=start_nodes,
                        index_layer=index_layer,
                        limits=limits,
                    )
                elif op in ("find_callers", "find_dependents", "find_imports"):
                    traversal_result = self.traversal_engine.execute_algorithm(
                        algorithm="dfs",
                        graph_view=graph_view,
                        start_nodes=start_nodes,
                        index_layer=index_layer,
                        limits=limits,
                    )
                else:
                    traversal_result = self.traversal_engine.execute_plan(
                        execution_plan=execution_plan,
                        graph_view=graph_view,
                        index_layer=index_layer,
                        limits=limits,
                    )

            execution_time_ms = (time.perf_counter() - t_exec_start) * 1000.0
            total_duration_ms = (time.perf_counter() - start_time) * 1000.0

            # 6. Adapt TraversalResult into Public QueryResult
            query_result = self._adapt_to_query_result(request, traversal_result)

            statistics = QueryStatistics(
                planning_time_ms=planning_time_ms,
                optimization_time_ms=optimization_time_ms,
                execution_time_ms=execution_time_ms,
                total_duration_ms=total_duration_ms,
                nodes_visited=len(traversal_result.visited_nodes) if traversal_result else 0,
                edges_visited=len(traversal_result.visited_edges) if traversal_result else 0,
                paths_explored=len(traversal_result.paths) if traversal_result else 0,
                result_count=len(query_result.nodes) or len(query_result.records) or len(query_result.paths),
            )

            diagnostics = QueryDiagnostics(
                query_summary=f"Executed operation '{request.operation}' on target '{request.target}'",
                planner_statistics={"logical_plan_id": logical_plan.plan_id, "execution_plan_id": execution_plan.execution_plan_id},
                traversal_statistics=traversal_result.diagnostics_summary if traversal_result else {},
            )

            return QueryResponse(
                request_id=request.request_id,
                status=ResponseStatus.SUCCESS,
                result=query_result,
                statistics=statistics,
                diagnostics=diagnostics,
            )

        except Exception as ex:
            total_duration_ms = (time.perf_counter() - start_time) * 1000.0
            err_detail = QueryErrorDetail(
                code=QueryErrorCode.EXECUTION_FAILED,
                message=str(ex),
                target=request.target,
            )
            return QueryResponse(
                request_id=request.request_id,
                status=ResponseStatus.FAILED,
                error=err_detail,
                statistics=QueryStatistics(total_duration_ms=total_duration_ms),
                diagnostics=QueryDiagnostics(errors=[str(ex)]),
            )

    def _build_engineering_query(self, request: QueryRequest) -> EngineeringQuery:
        """Converts QueryRequest into canonical EngineeringQuery AST."""
        builder = QueryBuilder(name=request.operation)
        target = request.target or "root"
        return builder.with_lookup(symbol_id_str=target, name=target).build()

    def _adapt_to_query_result(
        self,
        request: QueryRequest,
        traversal_result: Optional[TraversalResult],
    ) -> QueryResult:
        """Adapts raw TraversalResult into clean engineering QueryResult."""
        if not traversal_result:
            nodes = [{"id": request.target, "name": request.target}] if request.target else []
            return QueryResult(target=request.target, nodes=nodes)

        nodes = [{"id": nid, "name": nid} for nid in traversal_result.visited_nodes]
        edges = traversal_result.visited_edges
        paths = [p.nodes for p in traversal_result.paths]

        return QueryResult(
            target=request.target,
            nodes=nodes,
            edges=edges,
            paths=paths,
            metadata={"visited_count": len(nodes), "operation": request.operation},
        )


__all__ = ["QueryExecutor"]
