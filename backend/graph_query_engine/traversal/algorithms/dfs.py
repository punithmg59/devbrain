# backend/graph_query_engine/traversal/algorithms/dfs.py
"""Depth-First Search (DFS) graph algorithm implementation with cycle detection.
"""

from __future__ import annotations

import time
from typing import Any, Dict, List, Optional, Set, Tuple

from .base import BaseGraphAlgorithm
from ..context import TraversalExecutionContext
from ..metrics import TraversalMetrics
from ..result import TraversalPath, TraversalResult


class DepthFirstSearch(BaseGraphAlgorithm):
    """Depth-First Search (DFS) algorithm."""

    @property
    def name(self) -> str:
        return "DepthFirstSearch"

    def execute(
        self,
        context: TraversalExecutionContext,
        start_nodes: List[str],
        direction: str = "OUTGOING",
        max_depth: Optional[int] = None,
        **kwargs: Any,
    ) -> TraversalResult:
        start_time = time.perf_counter()
        limits = context.limits
        effective_max_depth = max_depth if max_depth is not None else limits.max_depth

        context.diagnostics.set_algorithm(self.name)
        context.diagnostics.record_info("Algorithm", f"Starting DFS from {start_nodes} (max_depth={effective_max_depth})")

        visited_set: Set[str] = set()
        visited_nodes: List[str] = []
        visited_edges: List[Dict[str, Any]] = []
        depth_map: Dict[str, int] = {}
        paths: List[TraversalPath] = []
        active_stack: Set[str] = set()
        detected_cycles: List[List[str]] = []

        edges_visited_count = 0

        def dfs_visit(node: str, depth: int, current_path_nodes: List[str], current_path_edges: List[Dict[str, Any]]):
            nonlocal edges_visited_count

            if depth > effective_max_depth:
                context.diagnostics.record_pruning("max_depth_reached")
                return

            if len(visited_nodes) >= limits.max_nodes:
                context.diagnostics.record_pruning("max_nodes_reached")
                return

            visited_set.add(node)
            visited_nodes.append(node)
            depth_map[node] = depth
            active_stack.add(node)

            paths.append(
                TraversalPath(
                    nodes=list(current_path_nodes),
                    edges=list(current_path_edges),
                    depth=depth,
                )
            )

            neighbors = self.get_neighbors(context.graph_view, node, direction=direction)
            for nbr, edge_meta in neighbors:
                edges_visited_count += 1
                if edge_meta:
                    visited_edges.append(edge_meta)

                if nbr in active_stack:
                    # Cycle detected!
                    cycle_start_idx = current_path_nodes.index(nbr) if nbr in current_path_nodes else 0
                    cycle_nodes = current_path_nodes[cycle_start_idx:] + [nbr]
                    detected_cycles.append(cycle_nodes)
                    context.diagnostics.record_warning("Cycle", f"Cycle detected: {' -> '.join(cycle_nodes)}")
                    continue

                if nbr not in visited_set:
                    dfs_visit(
                        nbr,
                        depth + 1,
                        current_path_nodes + [nbr],
                        current_path_edges + ([edge_meta] if edge_meta else []),
                    )

            active_stack.remove(node)

        for root in start_nodes:
            if root not in visited_set:
                dfs_visit(root, 0, [root], [])

        elapsed_ms = (time.perf_counter() - start_time) * 1000.0
        metrics = TraversalMetrics(
            nodes_visited=len(visited_nodes),
            edges_visited=edges_visited_count,
            paths_explored=len(paths),
            max_depth=max(depth_map.values()) if depth_map else 0,
            execution_duration_ms=elapsed_ms,
            algorithm_usage={self.name: 1},
        )

        return TraversalResult(
            visited_nodes=visited_nodes,
            visited_edges=visited_edges,
            paths=paths,
            depth_map=depth_map,
            root_nodes=start_nodes,
            leaf_nodes=[n for n in visited_nodes if n not in start_nodes and not self.get_neighbors(context.graph_view, n, direction)],
            metrics=metrics,
            diagnostics_summary=context.diagnostics.summary(),
            execution_time_ms=elapsed_ms,
        )


__all__ = ["DepthFirstSearch"]
