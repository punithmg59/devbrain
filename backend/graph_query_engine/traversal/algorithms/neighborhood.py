# backend/graph_query_engine/traversal/algorithms/neighborhood.py
"""Neighborhood Expansion graph algorithm implementation.
Expands k-hop neighborhood around start nodes.
"""

from __future__ import annotations

import time
from collections import deque
from typing import Any, Dict, List, Optional, Set

from .base import BaseGraphAlgorithm
from ..context import TraversalExecutionContext
from ..metrics import TraversalMetrics
from ..result import TraversalResult


class NeighborhoodExpansion(BaseGraphAlgorithm):
    """Multi-hop Neighborhood Expansion algorithm."""

    @property
    def name(self) -> str:
        return "NeighborhoodExpansion"

    def execute(
        self,
        context: TraversalExecutionContext,
        start_nodes: List[str],
        k_hops: int = 1,
        direction: str = "BOTH",
        **kwargs: Any,
    ) -> TraversalResult:
        start_time = time.perf_counter()
        context.diagnostics.set_algorithm(self.name)

        visited: Set[str] = set(start_nodes)
        neighborhood: List[str] = []
        depth_map: Dict[str, int] = {node: 0 for node in start_nodes}
        queue = deque([(node, 0) for node in start_nodes])
        edges_count = 0

        while queue:
            curr, depth = queue.popleft()
            if depth >= k_hops:
                continue

            for nbr, _ in self.get_neighbors(context.graph_view, curr, direction=direction):
                edges_count += 1
                if nbr not in visited:
                    visited.add(nbr)
                    neighborhood.append(nbr)
                    depth_map[nbr] = depth + 1
                    queue.append((nbr, depth + 1))

        elapsed_ms = (time.perf_counter() - start_time) * 1000.0
        metrics = TraversalMetrics(
            nodes_visited=len(visited),
            edges_visited=edges_count,
            max_depth=max(depth_map.values()) if depth_map else 0,
            execution_duration_ms=elapsed_ms,
            algorithm_usage={self.name: 1},
        )

        return TraversalResult(
            visited_nodes=neighborhood,
            depth_map=depth_map,
            root_nodes=start_nodes,
            leaf_nodes=neighborhood,
            metrics=metrics,
            diagnostics_summary=context.diagnostics.summary(),
            execution_time_ms=elapsed_ms,
        )


__all__ = ["NeighborhoodExpansion"]
