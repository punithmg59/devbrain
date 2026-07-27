# backend/graph_query_engine/traversal/algorithms/base.py
"""Abstract base class for all graph traversal algorithms in DevBrain.
"""

from __future__ import annotations

import abc
from typing import Any, List, Set, Dict, Optional, Tuple

from ..context import TraversalExecutionContext
from ..result import TraversalPath, TraversalResult


class BaseGraphAlgorithm(abc.ABC):
    """Abstract base class for pure graph algorithms operating on GraphView."""

    @property
    @abc.abstractmethod
    def name(self) -> str:
        """Name identifier of the algorithm."""

    @abc.abstractmethod
    def execute(
        self,
        context: TraversalExecutionContext,
        start_nodes: List[str],
        **kwargs: Any,
    ) -> TraversalResult:
        """Executes the graph algorithm against GraphView using TraversalExecutionContext."""

    @staticmethod
    def get_neighbors(graph_view: Any, node_id: str, direction: str = "OUTGOING") -> List[Tuple[str, Dict[str, Any]]]:
        """Unified helper to retrieve neighbors and edge attributes from GraphView across direction types.

        Returns:
            List of tuples: (neighbor_node_id, edge_metadata_dict)
        """
        neighbors: List[Tuple[str, Dict[str, Any]]] = []

        if hasattr(graph_view, "get_neighbors"):
            raw = graph_view.get_neighbors(node_id, direction=direction)
            for item in raw:
                if isinstance(item, tuple):
                    neighbors.append((item[0], item[1] if len(item) > 1 and isinstance(item[1], dict) else {}))
                elif isinstance(item, str):
                    neighbors.append((item, {}))
        elif hasattr(graph_view, "get_out_edges") and direction in ("OUTGOING", "BOTH"):
            edges = graph_view.get_out_edges(node_id)
            for e in edges:
                target = e.get("target") or e.get("target_id") or e.get("to")
                if target:
                    neighbors.append((str(target), dict(e)))
        elif hasattr(graph_view, "get_in_edges") and direction == "INCOMING":
            edges = graph_view.get_in_edges(node_id)
            for e in edges:
                source = e.get("source") or e.get("source_id") or e.get("from")
                if source:
                    neighbors.append((str(source), dict(e)))
        elif hasattr(graph_view, "neighbors"):
            for nbr in graph_view.neighbors(node_id):
                neighbors.append((str(nbr), {}))
        elif isinstance(graph_view, dict):
            if direction == "INCOMING":
                for src, adj in graph_view.items():
                    for item in adj:
                        nbr = item[0] if isinstance(item, tuple) else str(item)
                        meta = item[1] if isinstance(item, tuple) and len(item) > 1 and isinstance(item[1], dict) else {}
                        if nbr == node_id:
                            neighbors.append((str(src), meta))
            elif direction == "BOTH":
                # Outgoing
                for item in graph_view.get(node_id, []):
                    nbr = item[0] if isinstance(item, tuple) else str(item)
                    meta = item[1] if isinstance(item, tuple) and len(item) > 1 and isinstance(item[1], dict) else {}
                    neighbors.append((nbr, meta))
                # Incoming
                for src, adj in graph_view.items():
                    for item in adj:
                        nbr = item[0] if isinstance(item, tuple) else str(item)
                        meta = item[1] if isinstance(item, tuple) and len(item) > 1 and isinstance(item[1], dict) else {}
                        if nbr == node_id and str(src) != node_id:
                            neighbors.append((str(src), meta))
            else:
                # OUTGOING
                for item in graph_view.get(node_id, []):
                    nbr = item[0] if isinstance(item, tuple) else str(item)
                    meta = item[1] if isinstance(item, tuple) and len(item) > 1 and isinstance(item[1], dict) else {}
                    neighbors.append((nbr, meta))

        return neighbors


__all__ = ["BaseGraphAlgorithm"]
