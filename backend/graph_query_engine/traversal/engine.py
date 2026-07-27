# backend/graph_query_engine/traversal/engine.py
"""TraversalEngine main orchestrator for the DevBrain Graph Query Engine.
Consumes ExecutionPlan and GraphView to safely and efficiently execute graph traversals.
"""

from __future__ import annotations

import time
from typing import Any, Dict, List, Optional, Union

from .algorithms import (
    BaseGraphAlgorithm,
    BreadthFirstSearch,
    DepthFirstSearch,
    BidirectionalSearch,
    ReachabilityAnalysis,
    ShortestPath,
    ConnectedComponents,
    TopologicalTraversal,
    CycleDetection,
    AncestorDiscovery,
    DescendantDiscovery,
    NeighborhoodExpansion,
)
from .context import TraversalExecutionContext, TraversalLimits
from .diagnostics import TraversalDiagnostics
from .metrics import TraversalMetrics
from .pipeline import TraversalPipeline
from .result import TraversalResult
from .validation import TraversalValidator


class TraversalEngine:
    """Production-ready graph traversal execution engine.

    Executes graph algorithms and composable operator pipelines against an immutable GraphView.
    """

    ALGORITHM_MAP: Dict[str, BaseGraphAlgorithm] = {
        "bfs": BreadthFirstSearch(),
        "breadth_first_search": BreadthFirstSearch(),
        "dfs": DepthFirstSearch(),
        "depth_first_search": DepthFirstSearch(),
        "bidirectional": BidirectionalSearch(),
        "reachability": ReachabilityAnalysis(),
        "shortest_path": ShortestPath(),
        "connected_components": ConnectedComponents(),
        "topological": TopologicalTraversal(),
        "cycle_detection": CycleDetection(),
        "ancestors": AncestorDiscovery(),
        "descendants": DescendantDiscovery(),
        "neighborhood": NeighborhoodExpansion(),
    }

    def __init__(self, default_limits: Optional[TraversalLimits] = None) -> None:
        self.default_limits = default_limits or TraversalLimits()

    def execute_algorithm(
        self,
        algorithm: Union[str, BaseGraphAlgorithm],
        graph_view: Any,
        start_nodes: List[str],
        index_layer: Optional[Any] = None,
        limits: Optional[TraversalLimits] = None,
        **kwargs: Any,
    ) -> TraversalResult:
        """Executes a specific graph algorithm on GraphView."""
        val_report = TraversalValidator.validate_prerequisites(
            graph_view=graph_view,
            start_nodes=start_nodes,
            max_depth=limits.max_depth if limits else self.default_limits.max_depth,
        )
        if not val_report.valid:
            errors = [v.message for v in val_report.violations if v.severity == "ERROR"]
            raise ValueError(f"Traversal prerequisites validation failed: {'; '.join(errors)}")

        effective_limits = limits or self.default_limits
        context = TraversalExecutionContext(
            graph_view=graph_view,
            index_layer=index_layer,
            limits=effective_limits,
            diagnostics=TraversalDiagnostics(),
            metrics=TraversalMetrics(),
        )

        algo_inst: BaseGraphAlgorithm
        if isinstance(algorithm, str):
            key = algorithm.lower().strip()
            if key not in self.ALGORITHM_MAP:
                raise KeyError(f"Unknown algorithm '{algorithm}'. Available: {list(self.ALGORITHM_MAP.keys())}")
            algo_inst = self.ALGORITHM_MAP[key]
        elif isinstance(algorithm, BaseGraphAlgorithm):
            algo_inst = algorithm
        else:
            raise TypeError("Algorithm must be string name or BaseGraphAlgorithm instance")

        result = algo_inst.execute(context, start_nodes=start_nodes, **kwargs)

        res_val = TraversalValidator.validate_result(result)
        if not res_val.valid:
            errors = [v.message for v in res_val.violations if v.severity == "ERROR"]
            raise ValueError(f"Traversal result validation failed: {'; '.join(errors)}")

        return result

    def execute_pipeline(
        self,
        pipeline: TraversalPipeline,
        graph_view: Any,
        start_nodes: List[str],
        index_layer: Optional[Any] = None,
        limits: Optional[TraversalLimits] = None,
    ) -> TraversalResult:
        """Executes a composable TraversalPipeline."""
        val_report = TraversalValidator.validate_prerequisites(
            graph_view=graph_view,
            start_nodes=start_nodes,
            max_depth=limits.max_depth if limits else self.default_limits.max_depth,
        )
        if not val_report.valid:
            errors = [v.message for v in val_report.violations if v.severity == "ERROR"]
            raise ValueError(f"Traversal pipeline prerequisites validation failed: {'; '.join(errors)}")

        effective_limits = limits or self.default_limits
        context = TraversalExecutionContext(
            graph_view=graph_view,
            index_layer=index_layer,
            limits=effective_limits,
            diagnostics=TraversalDiagnostics(),
            metrics=TraversalMetrics(),
        )

        return pipeline.execute(context, start_nodes)

    def execute_plan(
        self,
        execution_plan: Any,
        graph_view: Any,
        index_layer: Optional[Any] = None,
        limits: Optional[TraversalLimits] = None,
    ) -> TraversalResult:
        """Executes an ExecutionPlan by extracting stages or root nodes and executing traversal."""
        start_nodes: List[str] = []

        # Extract root nodes or execution specs from execution_plan if available
        if hasattr(execution_plan, "stages") and execution_plan.stages:
            for stage in execution_plan.stages:
                if hasattr(stage, "operators"):
                    for op in stage.operators:
                        if hasattr(op, "params") and isinstance(op.params, dict):
                            if "root" in op.params:
                                start_nodes.append(str(op.params["root"]))
                            elif "start_nodes" in op.params and isinstance(op.params["start_nodes"], list):
                                start_nodes.extend([str(x) for x in op.params["start_nodes"]])

        if not start_nodes and hasattr(graph_view, "get_all_nodes"):
            all_n = graph_view.get_all_nodes()
            if all_n:
                start_nodes = [list(all_n)[0]]

        if not start_nodes:
            start_nodes = ["root"]

        # Default execution algorithm for ExecutionPlan is BFS
        return self.execute_algorithm(
            algorithm="bfs",
            graph_view=graph_view,
            start_nodes=start_nodes,
            index_layer=index_layer,
            limits=limits,
        )


__all__ = ["TraversalEngine"]
