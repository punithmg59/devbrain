# backend/graph_query_engine/traversal/algorithms/reachability.py
"""Reachability Analysis graph algorithm implementation.
Determines whether target node(s) are reachable from source node(s).
"""

from __future__ import annotations

import time
from collections import deque
from typing import Any, Dict, List, Optional, Set

from .base import BaseGraphAlgorithm
from ..context import TraversalExecutionContext
from ..metrics import TraversalMetrics
from ..result import TraversalPath, TraversalResult


class ReachabilityAnalysis(BaseGraphAlgorithm):
    """Reachability Analysis algorithm."""

    @property
    def name(self) -> str:
        return "ReachabilityAnalysis"

    def execute(
        self,
        context: TraversalExecutionContext,
        start_nodes: List[str],
        target_nodes: Optional[List[str]] = None,
        direction: str = "OUTGOING",
        **kwargs: Any,
    ) -> TraversalResult:
        start_time = time.perf_counter()
        context.diagnostics.set_algorithm(self.name)

        targets_set = set(target_nodes) if target_nodes else set()
        visited: Set[str] = set()
        reachable_targets: Set[str] = set()
        depth_map: Dict[str, int] = {}
        queue = deque()

        for root in start_nodes:
            if root not in visited:
                visited.add(root)
                depth_map[root] = 0
                queue.append((root, 0))
                if root in targets_set:
                    reachable_targets.add(root)

        edges_count = 0
        while queue:
            curr, depth = queue.popleft()
            if depth >= context.limits.max_depth:
                continue

            for nbr, edge_meta in self.get_neighbors(context.graph_view, curr, direction=direction):
                edges_count += 1
                if nbr not in visited:
                    visited.add(nbr)
                    depth_map[nbr] = depth + 1
                    queue.append((nbr, depth + 1))
                    if nbr in targets_set:
                        reachable_targets.add(nbr)

        context.diagnostics.record_info(
            "Algorithm", f"Reachability analysis found {len(reachable_targets)} reachable targets out of {len(targets_set)}"
        )

        elapsed_ms = (time.perf_counter() - start_time) * 1000.0
        metrics = TraversalMetrics(
            nodes_visited=len(visited),
            edges_visited=edges_count,
            execution_duration_ms=elapsed_ms,
            algorithm_usage={self.name: 1},
        )

        return TraversalResult(
            visited_nodes=list(visited),
            root_nodes=start_nodes,
            leaf_nodes=list(reachable_targets),
            depth_map=depth_map,
            metrics=metrics,
            diagnostics_summary=context.diagnostics.summary(),
            execution_time_ms=elapsed_ms,
        )


__all__ = ["ReachabilityAnalysis"]
