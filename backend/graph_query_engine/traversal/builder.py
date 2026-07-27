# backend/graph_query_engine/traversal/builder.py
"""Fluent builders for constructing TraversalResult, TraversalExecutionContext, and reports.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from pydantic import BaseModel

from .context import TraversalExecutionContext, TraversalLimits
from .diagnostics import TraversalDiagnostics
from .metrics import TraversalMetrics
from .result import TraversalPath, TraversalResult


class TraversalResultBuilder:
    """Fluent builder for TraversalResult."""

    def __init__(self) -> None:
        self._visited_nodes: List[str] = []
        self._visited_edges: List[Dict[str, Any]] = []
        self._paths: List[TraversalPath] = []
        self._depth_map: Dict[str, int] = {}
        self._root_nodes: List[str] = []
        self._leaf_nodes: List[str] = []
        self._metrics: TraversalMetrics = TraversalMetrics()
        self._diagnostics_summary: Dict[str, Any] = {}
        self._execution_time_ms: float = 0.0

    def with_visited_nodes(self, nodes: List[str]) -> TraversalResultBuilder:
        self._visited_nodes = list(nodes)
        return self

    def with_visited_edges(self, edges: List[Dict[str, Any]]) -> TraversalResultBuilder:
        self._visited_edges = list(edges)
        return self

    def with_paths(self, paths: List[TraversalPath]) -> TraversalResultBuilder:
        self._paths = list(paths)
        return self

    def with_depth_map(self, depth_map: Dict[str, int]) -> TraversalResultBuilder:
        self._depth_map = dict(depth_map)
        return self

    def with_root_nodes(self, roots: List[str]) -> TraversalResultBuilder:
        self._root_nodes = list(roots)
        return self

    def with_leaf_nodes(self, leaves: List[str]) -> TraversalResultBuilder:
        self._leaf_nodes = list(leaves)
        return self

    def with_metrics(self, metrics: TraversalMetrics) -> TraversalResultBuilder:
        self._metrics = metrics
        return self

    def with_diagnostics_summary(self, summary: Dict[str, Any]) -> TraversalResultBuilder:
        self._diagnostics_summary = dict(summary)
        return self

    def with_execution_time_ms(self, duration_ms: float) -> TraversalResultBuilder:
        self._execution_time_ms = duration_ms
        return self

    def build(self) -> TraversalResult:
        return TraversalResult(
            visited_nodes=self._visited_nodes,
            visited_edges=self._visited_edges,
            paths=self._paths,
            depth_map=self._depth_map,
            root_nodes=self._root_nodes,
            leaf_nodes=self._leaf_nodes,
            metrics=self._metrics,
            diagnostics_summary=self._diagnostics_summary,
            execution_time_ms=self._execution_time_ms,
        )


class ExecutionContextBuilder:
    """Fluent builder for TraversalExecutionContext."""

    def __init__(self) -> None:
        self._graph_view: Any = None
        self._index_layer: Optional[Any] = None
        self._limits: TraversalLimits = TraversalLimits()
        self._diagnostics: TraversalDiagnostics = TraversalDiagnostics()
        self._metrics: TraversalMetrics = TraversalMetrics()

    def with_graph_view(self, graph_view: Any) -> ExecutionContextBuilder:
        self._graph_view = graph_view
        return self

    def with_index_layer(self, index_layer: Any) -> ExecutionContextBuilder:
        self._index_layer = index_layer
        return self

    def with_limits(self, limits: TraversalLimits) -> ExecutionContextBuilder:
        self._limits = limits
        return self

    def build(self) -> TraversalExecutionContext:
        if self._graph_view is None:
            raise ValueError("graph_view must be specified")
        return TraversalExecutionContext(
            graph_view=self._graph_view,
            index_layer=self._index_layer,
            limits=self._limits,
            diagnostics=self._diagnostics,
            metrics=self._metrics,
        )


class TraversalReportBuilder:
    """Builder for aggregated Traversal Report objects."""

    def __init__(self) -> None:
        self._result: Optional[TraversalResult] = None

    def with_result(self, result: TraversalResult) -> TraversalReportBuilder:
        self._result = result
        return self

    def build(self) -> Dict[str, Any]:
        if self._result is None:
            raise ValueError("result must be set before building report")
        return {
            "timestamp": str(self._result.timestamp),
            "visited_node_count": len(self._result.visited_nodes),
            "visited_edge_count": len(self._result.visited_edges),
            "path_count": len(self._result.paths),
            "root_nodes": self._result.root_nodes,
            "execution_time_ms": self._result.execution_time_ms,
            "metrics": self._result.metrics.model_dump(),
            "diagnostics": self._result.diagnostics_summary,
        }


class TraversalMetricsBuilder:
    """Fluent builder for TraversalMetrics."""

    def __init__(self) -> None:
        self._metrics = TraversalMetrics()

    def add_nodes_visited(self, count: int) -> TraversalMetricsBuilder:
        self._metrics = self._metrics.with_increment(nodes_visited=count)
        return self

    def add_edges_visited(self, count: int) -> TraversalMetricsBuilder:
        self._metrics = self._metrics.with_increment(edges_visited=count)
        return self

    def set_duration(self, ms: float) -> TraversalMetricsBuilder:
        self._metrics = self._metrics.with_increment(execution_duration_ms=ms)
        return self

    def build(self) -> TraversalMetrics:
        return self._metrics


__all__ = [
    "TraversalResultBuilder",
    "ExecutionContextBuilder",
    "TraversalReportBuilder",
    "TraversalMetricsBuilder",
]
