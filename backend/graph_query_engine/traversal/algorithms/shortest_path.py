# backend/graph_query_engine/traversal/algorithms/shortest_path.py
"""Unweighted Shortest Path graph algorithm implementation using BFS.
"""

from __future__ import annotations

import time
from collections import deque
from typing import Any, Dict, List, Optional, Set, Tuple

from .base import BaseGraphAlgorithm
from ..context import TraversalExecutionContext
from ..metrics import TraversalMetrics
from ..result import TraversalPath, TraversalResult


class ShortestPath(BaseGraphAlgorithm):
    """Unweighted Shortest Path algorithm."""

    @property
    def name(self) -> str:
        return "ShortestPath"

    def execute(
        self,
        context: TraversalExecutionContext,
        start_nodes: List[str],
        target_node: Optional[str] = None,
        direction: str = "OUTGOING",
        **kwargs: Any,
    ) -> TraversalResult:
        start_time = time.perf_counter()
        context.diagnostics.set_algorithm(self.name)

        if not start_nodes or not target_node:
            raise ValueError("ShortestPath requires start_nodes and target_node")

        src = start_nodes[0]
        tgt = target_node

        if src == tgt:
            path = TraversalPath(nodes=[src], edges=[], depth=0)
            elapsed_ms = (time.perf_counter() - start_time) * 1000.0
            return TraversalResult(
                visited_nodes=[src],
                paths=[path],
                root_nodes=[src],
                leaf_nodes=[tgt],
                metrics=TraversalMetrics(nodes_visited=1, paths_explored=1, execution_duration_ms=elapsed_ms),
                diagnostics_summary=context.diagnostics.summary(),
                execution_time_ms=elapsed_ms,
            )

        parent_map: Dict[str, Tuple[str, Dict[str, Any]]] = {}
        visited: Set[str] = {src}
        queue = deque([src])
        found = False
        edges_count = 0

        while queue:
            curr = queue.popleft()
            if curr == tgt:
                found = True
                break

            for nbr, edge_meta in self.get_neighbors(context.graph_view, curr, direction=direction):
                edges_count += 1
                if nbr not in visited:
                    visited.add(nbr)
                    parent_map[nbr] = (curr, edge_meta)
                    queue.append(nbr)
                    if nbr == tgt:
                        found = True
                        break
            if found:
                break

        paths: List[TraversalPath] = []
        if found:
            curr = tgt
            path_nodes = [curr]
            path_edges = []
            while curr in parent_map:
                parent, edge_info = parent_map[curr]
                path_nodes.append(parent)
                if edge_info:
                    path_edges.append(edge_info)
                curr = parent
            path_nodes.reverse()
            path_edges.reverse()
            paths.append(TraversalPath(nodes=path_nodes, edges=path_edges, depth=len(path_nodes) - 1))
            context.diagnostics.record_info("Algorithm", f"Shortest path found: {path_nodes}")
        else:
            context.diagnostics.record_warning("Algorithm", f"No shortest path found between '{src}' and '{tgt}'")

        elapsed_ms = (time.perf_counter() - start_time) * 1000.0
        metrics = TraversalMetrics(
            nodes_visited=len(visited),
            edges_visited=edges_count,
            paths_explored=len(paths),
            max_depth=paths[0].depth if paths else 0,
            execution_duration_ms=elapsed_ms,
            algorithm_usage={self.name: 1},
        )

        return TraversalResult(
            visited_nodes=list(visited),
            paths=paths,
            root_nodes=[src],
            leaf_nodes=[tgt] if found else [],
            metrics=metrics,
            diagnostics_summary=context.diagnostics.summary(),
            execution_time_ms=elapsed_ms,
        )


__all__ = ["ShortestPath"]
