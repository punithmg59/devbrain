# backend/graph_query_engine/traversal/algorithms/connected_components.py
"""Connected Components graph algorithm implementation.
Discovers weakly connected components across a repository scope or node set.
"""

from __future__ import annotations

import time
from collections import deque
from typing import Any, Dict, List, Set

from .base import BaseGraphAlgorithm
from ..context import TraversalExecutionContext
from ..metrics import TraversalMetrics
from ..result import TraversalPath, TraversalResult


class ConnectedComponents(BaseGraphAlgorithm):
    """Connected Components discovery algorithm."""

    @property
    def name(self) -> str:
        return "ConnectedComponents"

    def execute(
        self,
        context: TraversalExecutionContext,
        start_nodes: List[str],
        **kwargs: Any,
    ) -> TraversalResult:
        start_time = time.perf_counter()
        context.diagnostics.set_algorithm(self.name)

        all_nodes: Set[str] = set(start_nodes)
        if hasattr(context.graph_view, "get_all_nodes"):
            all_nodes.update(context.graph_view.get_all_nodes())
        elif hasattr(context.graph_view, "nodes"):
            all_nodes.update(context.graph_view.nodes)
        elif isinstance(context.graph_view, dict):
            all_nodes.update(context.graph_view.keys())

        visited: Set[str] = set()
        components: List[List[str]] = []
        edges_count = 0

        for node in all_nodes:
            if node not in visited:
                comp: List[str] = []
                queue = deque([node])
                visited.add(node)
                while queue:
                    curr = queue.popleft()
                    comp.append(curr)
                    # Weakly connected: inspect both OUTGOING and INCOMING
                    for direction in ("OUTGOING", "INCOMING"):
                        for nbr, _ in self.get_neighbors(context.graph_view, curr, direction=direction):
                            edges_count += 1
                            if nbr not in visited:
                                visited.add(nbr)
                                queue.append(nbr)
                components.append(comp)

        context.diagnostics.record_info("Algorithm", f"Discovered {len(components)} connected components")

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
            leaf_nodes=[c[0] for c in components if c],
            metrics=metrics,
            diagnostics_summary=context.diagnostics.summary(),
            execution_time_ms=elapsed_ms,
        )


__all__ = ["ConnectedComponents"]
