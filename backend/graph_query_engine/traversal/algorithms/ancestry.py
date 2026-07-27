# backend/graph_query_engine/traversal/algorithms/ancestry.py
"""Ancestor and Descendant discovery graph algorithms.
Discovers transitive callers/dependencies (ancestors) or callees/dependents (descendants).
"""

from __future__ import annotations

import time
from collections import deque
from typing import Any, Dict, List, Optional, Set

from .base import BaseGraphAlgorithm
from ..context import TraversalExecutionContext
from ..metrics import TraversalMetrics
from ..result import TraversalPath, TraversalResult


class AncestorDiscovery(BaseGraphAlgorithm):
    """Discovers all transitive upstream ancestors (incoming edge traversal)."""

    @property
    def name(self) -> str:
        return "AncestorDiscovery"

    def execute(
        self,
        context: TraversalExecutionContext,
        start_nodes: List[str],
        max_depth: Optional[int] = None,
        **kwargs: Any,
    ) -> TraversalResult:
        start_time = time.perf_counter()
        effective_max_depth = max_depth if max_depth is not None else context.limits.max_depth
        context.diagnostics.set_algorithm(self.name)

        visited: Set[str] = set(start_nodes)
        ancestors: List[str] = []
        depth_map: Dict[str, int] = {node: 0 for node in start_nodes}
        queue = deque([(node, 0) for node in start_nodes])
        edges_count = 0

        while queue:
            curr, depth = queue.popleft()
            if depth >= effective_max_depth:
                continue

            for nbr, _ in self.get_neighbors(context.graph_view, curr, direction="INCOMING"):
                edges_count += 1
                if nbr not in visited:
                    visited.add(nbr)
                    ancestors.append(nbr)
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
            visited_nodes=ancestors,
            depth_map=depth_map,
            root_nodes=start_nodes,
            leaf_nodes=ancestors,
            metrics=metrics,
            diagnostics_summary=context.diagnostics.summary(),
            execution_time_ms=elapsed_ms,
        )


class DescendantDiscovery(BaseGraphAlgorithm):
    """Discovers all transitive downstream descendants (outgoing edge traversal)."""

    @property
    def name(self) -> str:
        return "DescendantDiscovery"

    def execute(
        self,
        context: TraversalExecutionContext,
        start_nodes: List[str],
        max_depth: Optional[int] = None,
        **kwargs: Any,
    ) -> TraversalResult:
        start_time = time.perf_counter()
        effective_max_depth = max_depth if max_depth is not None else context.limits.max_depth
        context.diagnostics.set_algorithm(self.name)

        visited: Set[str] = set(start_nodes)
        descendants: List[str] = []
        depth_map: Dict[str, int] = {node: 0 for node in start_nodes}
        queue = deque([(node, 0) for node in start_nodes])
        edges_count = 0

        while queue:
            curr, depth = queue.popleft()
            if depth >= effective_max_depth:
                continue

            for nbr, _ in self.get_neighbors(context.graph_view, curr, direction="OUTGOING"):
                edges_count += 1
                if nbr not in visited:
                    visited.add(nbr)
                    descendants.append(nbr)
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
            visited_nodes=descendants,
            depth_map=depth_map,
            root_nodes=start_nodes,
            leaf_nodes=descendants,
            metrics=metrics,
            diagnostics_summary=context.diagnostics.summary(),
            execution_time_ms=elapsed_ms,
        )


__all__ = ["AncestorDiscovery", "DescendantDiscovery"]
