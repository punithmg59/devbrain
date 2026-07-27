# backend/graph_query_engine/traversal/algorithms/topological.py
"""Topological Sort / Traversal graph algorithm implementation.
Produces a linear ordering of nodes for Directed Acyclic Graphs (DAGs).
"""

from __future__ import annotations

import time
from collections import deque
from typing import Any, Dict, List, Set

from .base import BaseGraphAlgorithm
from ..context import TraversalExecutionContext
from ..metrics import TraversalMetrics
from ..result import TraversalResult


class TopologicalTraversal(BaseGraphAlgorithm):
    """Topological Traversal algorithm (Kahn's algorithm)."""

    @property
    def name(self) -> str:
        return "TopologicalTraversal"

    def execute(
        self,
        context: TraversalExecutionContext,
        start_nodes: List[str],
        **kwargs: Any,
    ) -> TraversalResult:
        start_time = time.perf_counter()
        context.diagnostics.set_algorithm(self.name)

        # Collect reachable subgraph nodes
        visited: Set[str] = set()
        queue = deque(start_nodes)
        for root in start_nodes:
            visited.add(root)

        edges_count = 0
        in_degree: Dict[str, int] = {node: 0 for node in start_nodes}
        adj: Dict[str, List[str]] = {}

        while queue:
            curr = queue.popleft()
            nbrs = self.get_neighbors(context.graph_view, curr, direction="OUTGOING")
            adj[curr] = [nbr for nbr, _ in nbrs]

            for nbr, _ in nbrs:
                edges_count += 1
                if nbr not in visited:
                    visited.add(nbr)
                    queue.append(nbr)
                in_degree[nbr] = in_degree.get(nbr, 0) + 1

        # Kahn's algorithm
        zero_in_queue = deque([n for n, deg in in_degree.items() if deg == 0])
        topo_order: List[str] = []

        while zero_in_queue:
            curr = zero_in_queue.popleft()
            topo_order.append(curr)

            for nbr in adj.get(curr, []):
                in_degree[nbr] -= 1
                if in_degree[nbr] == 0:
                    zero_in_queue.append(nbr)

        if len(topo_order) < len(visited):
            context.diagnostics.record_warning(
                "Cycle", "Graph contains cycle(s); topological sort is partial."
            )

        elapsed_ms = (time.perf_counter() - start_time) * 1000.0
        metrics = TraversalMetrics(
            nodes_visited=len(visited),
            edges_visited=edges_count,
            execution_duration_ms=elapsed_ms,
            algorithm_usage={self.name: 1},
        )

        return TraversalResult(
            visited_nodes=topo_order,
            root_nodes=start_nodes,
            leaf_nodes=[n for n, deg in in_degree.items() if deg == 0],
            metrics=metrics,
            diagnostics_summary=context.diagnostics.summary(),
            execution_time_ms=elapsed_ms,
        )


__all__ = ["TopologicalTraversal"]
