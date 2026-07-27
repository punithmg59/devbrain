# backend/graph_query_engine/traversal/algorithms/bidirectional.py
"""Bidirectional Search graph algorithm implementation.
Expands concurrently from source and target nodes until frontiers intersect.
"""

from __future__ import annotations

import time
from collections import deque
from typing import Any, Dict, List, Optional, Set, Tuple

from .base import BaseGraphAlgorithm
from ..context import TraversalExecutionContext
from ..metrics import TraversalMetrics
from ..result import TraversalPath, TraversalResult


class BidirectionalSearch(BaseGraphAlgorithm):
    """Bidirectional Search algorithm between a source node and target node."""

    @property
    def name(self) -> str:
        return "BidirectionalSearch"

    def execute(
        self,
        context: TraversalExecutionContext,
        start_nodes: List[str],
        target_node: Optional[str] = None,
        **kwargs: Any,
    ) -> TraversalResult:
        start_time = time.perf_counter()
        context.diagnostics.set_algorithm(self.name)

        if not start_nodes or not target_node:
            raise ValueError("BidirectionalSearch requires at least one start_node and a target_node")

        src = start_nodes[0]
        tgt = target_node

        if src == tgt:
            path = TraversalPath(nodes=[src], edges=[], depth=0)
            elapsed_ms = (time.perf_counter() - start_time) * 1000.0
            return TraversalResult(
                visited_nodes=[src],
                paths=[path],
                depth_map={src: 0},
                root_nodes=[src],
                leaf_nodes=[tgt],
                metrics=TraversalMetrics(nodes_visited=1, paths_explored=1, execution_duration_ms=elapsed_ms),
                diagnostics_summary=context.diagnostics.summary(),
                execution_time_ms=elapsed_ms,
            )

        forward_visited: Dict[str, Tuple[Optional[str], Dict[str, Any]]] = {src: (None, {})}
        backward_visited: Dict[str, Tuple[Optional[str], Dict[str, Any]]] = {tgt: (None, {})}

        forward_queue = deque([src])
        backward_queue = deque([tgt])

        intersect_node: Optional[str] = None
        edges_count = 0

        while forward_queue and backward_queue:
            # Expand forward step
            if forward_queue:
                curr_fwd = forward_queue.popleft()
                for nbr, edge_meta in self.get_neighbors(context.graph_view, curr_fwd, direction="OUTGOING"):
                    edges_count += 1
                    if nbr not in forward_visited:
                        forward_visited[nbr] = (curr_fwd, edge_meta)
                        forward_queue.append(nbr)
                    if nbr in backward_visited:
                        intersect_node = nbr
                        break
            if intersect_node:
                break

            # Expand backward step
            if backward_queue:
                curr_bwd = backward_queue.popleft()
                for nbr, edge_meta in self.get_neighbors(context.graph_view, curr_bwd, direction="INCOMING"):
                    edges_count += 1
                    if nbr not in backward_visited:
                        backward_visited[nbr] = (curr_bwd, edge_meta)
                        backward_queue.append(nbr)
                    if nbr in forward_visited:
                        intersect_node = nbr
                        break
            if intersect_node:
                break

        paths: List[TraversalPath] = []
        visited_all = list(set(forward_visited.keys()).union(backward_visited.keys()))

        if intersect_node:
            context.diagnostics.record_info("Algorithm", f"Bidirectional search intersected at '{intersect_node}'")

            # Reconstruct path from src to intersect
            fwd_nodes = []
            curr = intersect_node
            fwd_edges = []
            while curr is not None:
                fwd_nodes.append(curr)
                parent, edge_info = forward_visited[curr]
                if edge_info:
                    fwd_edges.append(edge_info)
                curr = parent
            fwd_nodes.reverse()
            fwd_edges.reverse()

            # Reconstruct path from intersect to tgt
            bwd_nodes = []
            curr = backward_visited[intersect_node][0]
            bwd_edges = []
            while curr is not None:
                bwd_nodes.append(curr)
                parent, edge_info = backward_visited[curr]
                if edge_info:
                    bwd_edges.append(edge_info)
                curr = parent

            full_nodes = fwd_nodes + bwd_nodes
            full_edges = fwd_edges + bwd_edges
            paths.append(TraversalPath(nodes=full_nodes, edges=full_edges, depth=len(full_nodes) - 1))
        else:
            context.diagnostics.record_warning("Algorithm", f"No path found between '{src}' and '{tgt}'")

        elapsed_ms = (time.perf_counter() - start_time) * 1000.0
        metrics = TraversalMetrics(
            nodes_visited=len(visited_all),
            edges_visited=edges_count,
            paths_explored=len(paths),
            max_depth=paths[0].depth if paths else 0,
            execution_duration_ms=elapsed_ms,
            algorithm_usage={self.name: 1},
        )

        return TraversalResult(
            visited_nodes=visited_all,
            paths=paths,
            root_nodes=[src],
            leaf_nodes=[tgt],
            metrics=metrics,
            diagnostics_summary=context.diagnostics.summary(),
            execution_time_ms=elapsed_ms,
        )


__all__ = ["BidirectionalSearch"]
