# backend/graph_query_engine/traversal/algorithms/cycle_detection.py
"""Cycle Detection graph algorithm implementation using Tarjan / DFS back-edge detection.
"""

from __future__ import annotations

import time
from typing import Any, Dict, List, Set

from .base import BaseGraphAlgorithm
from ..context import TraversalExecutionContext
from ..metrics import TraversalMetrics
from ..result import TraversalPath, TraversalResult


class CycleDetection(BaseGraphAlgorithm):
    """Cycle Detection algorithm."""

    @property
    def name(self) -> str:
        return "CycleDetection"

    def execute(
        self,
        context: TraversalExecutionContext,
        start_nodes: List[str],
        direction: str = "OUTGOING",
        **kwargs: Any,
    ) -> TraversalResult:
        start_time = time.perf_counter()
        context.diagnostics.set_algorithm(self.name)

        visited: Set[str] = set()
        active_stack: Set[str] = set()
        cycles: List[TraversalPath] = []
        visited_nodes: List[str] = []
        edges_count = 0

        def dfs(node: str, path_nodes: List[str]):
            nonlocal edges_count
            visited.add(node)
            visited_nodes.append(node)
            active_stack.add(node)

            for nbr, edge_meta in self.get_neighbors(context.graph_view, node, direction=direction):
                edges_count += 1
                if nbr in active_stack:
                    # Found cycle
                    cycle_start = path_nodes.index(nbr) if nbr in path_nodes else 0
                    cycle_subpath = path_nodes[cycle_start:] + [nbr]
                    cycles.append(
                        TraversalPath(
                            nodes=cycle_subpath,
                            edges=[],
                            depth=len(cycle_subpath) - 1,
                        )
                    )
                    context.diagnostics.record_warning("Cycle", f"Cycle detected: {' -> '.join(cycle_subpath)}")
                elif nbr not in visited:
                    dfs(nbr, path_nodes + [nbr])

            active_stack.remove(node)

        for root in start_nodes:
            if root not in visited:
                dfs(root, [root])

        elapsed_ms = (time.perf_counter() - start_time) * 1000.0
        metrics = TraversalMetrics(
            nodes_visited=len(visited),
            edges_visited=edges_count,
            paths_explored=len(cycles),
            execution_duration_ms=elapsed_ms,
            algorithm_usage={self.name: 1},
        )

        return TraversalResult(
            visited_nodes=visited_nodes,
            paths=cycles,
            root_nodes=start_nodes,
            metrics=metrics,
            diagnostics_summary=context.diagnostics.summary(),
            execution_time_ms=elapsed_ms,
        )


__all__ = ["CycleDetection"]
