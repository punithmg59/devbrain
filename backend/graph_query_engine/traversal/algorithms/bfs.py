# backend/graph_query_engine/traversal/algorithms/bfs.py
"""Breadth-First Search (BFS) graph algorithm implementation.
"""

from __future__ import annotations

import time
from collections import deque
from typing import Any, Dict, List, Set

from .base import BaseGraphAlgorithm
from ..context import TraversalExecutionContext
from ..metrics import TraversalMetrics
from ..result import TraversalPath, TraversalResult


class BreadthFirstSearch(BaseGraphAlgorithm):
    """Breadth-First Search (BFS) algorithm."""

    @property
    def name(self) -> str:
        return "BreadthFirstSearch"

    def execute(
        self,
        context: TraversalExecutionContext,
        start_nodes: List[str],
        direction: str = "OUTGOING",
        max_depth: Optional[int] = None,
        target_node: Optional[str] = None,
        **kwargs: Any,
    ) -> TraversalResult:
        start_time = time.perf_counter()
        limits = context.limits
        effective_max_depth = max_depth if max_depth is not None else limits.max_depth

        context.diagnostics.set_algorithm(self.name)
        context.diagnostics.record_info("Algorithm", f"Starting BFS from {start_nodes} (max_depth={effective_max_depth})")

        visited_set: Set[str] = set()
        visited_nodes: List[str] = []
        visited_edges: List[Dict[str, Any]] = []
        depth_map: Dict[str, int] = {}
        paths: List[TraversalPath] = []
        parent_map: Dict[str, Tuple[str, Dict[str, Any]]] = {}

        queue = deque()
        for root in start_nodes:
            if root not in visited_set:
                visited_set.add(root)
                visited_nodes.append(root)
                depth_map[root] = 0
                queue.append((root, 0))

        nodes_visited_count = len(visited_nodes)
        edges_visited_count = 0
        leaf_nodes: List[str] = []

        while queue:
            curr_node, curr_depth = queue.popleft()

            if target_node and curr_node == target_node:
                context.diagnostics.record_info("Pruning", f"Target node '{target_node}' reached; early termination.")
                break

            if curr_depth >= effective_max_depth:
                context.diagnostics.record_pruning("max_depth_reached")
                continue

            if nodes_visited_count >= limits.max_nodes:
                context.diagnostics.record_pruning("max_nodes_reached")
                context.diagnostics.record_warning("Limit", f"Max node limit ({limits.max_nodes}) reached")
                break

            neighbors = self.get_neighbors(context.graph_view, curr_node, direction=direction)
            has_unvisited_neighbor = False

            for nbr, edge_meta in neighbors:
                edges_visited_count += 1
                if edges_visited_count >= limits.max_edges:
                    context.diagnostics.record_pruning("max_edges_reached")
                    break

                if edge_meta:
                    visited_edges.append(edge_meta)

                if nbr not in visited_set:
                    visited_set.add(nbr)
                    visited_nodes.append(nbr)
                    nodes_visited_count += 1
                    depth_map[nbr] = curr_depth + 1
                    parent_map[nbr] = (curr_node, edge_meta)
                    has_unvisited_neighbor = True
                    queue.append((nbr, curr_depth + 1))

            if not has_unvisited_neighbor and curr_node not in start_nodes:
                leaf_nodes.append(curr_node)

        # Reconstruct paths for discovered nodes
        for node in visited_nodes:
            path_nodes = [node]
            path_edges = []
            curr = node
            while curr in parent_map:
                parent, edge_info = parent_map[curr]
                path_nodes.append(parent)
                if edge_info:
                    path_edges.append(edge_info)
                curr = parent
            path_nodes.reverse()
            path_edges.reverse()
            paths.append(
                TraversalPath(
                    nodes=path_nodes,
                    edges=path_edges,
                    depth=len(path_nodes) - 1,
                )
            )

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
            leaf_nodes=leaf_nodes,
            metrics=metrics,
            diagnostics_summary=context.diagnostics.summary(),
            execution_time_ms=elapsed_ms,
        )


__all__ = ["BreadthFirstSearch"]
