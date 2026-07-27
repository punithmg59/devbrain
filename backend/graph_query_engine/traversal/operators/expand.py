# backend/graph_query_engine/traversal/operators/expand.py
"""NeighborExpand, EdgeFilter, and PathExpand traversal operators.
"""

from __future__ import annotations

from typing import Any, List, Optional
from pydantic import Field

from .base import TraversalOperator
from ..algorithms.base import BaseGraphAlgorithm
from ..context import TraversalExecutionContext


class NeighborExpandOperator(TraversalOperator):
    """Operator that expands 1-hop neighbors."""

    direction: str = Field("OUTGOING", description="Expansion direction: OUTGOING, INCOMING, BOTH")

    @property
    def operator_name(self) -> str:
        return "NeighborExpand"

    def execute(
        self,
        context: TraversalExecutionContext,
        input_nodes: List[str],
        **kwargs: Any,
    ) -> List[str]:
        expanded: List[str] = []
        for node in input_nodes:
            nbrs = BaseGraphAlgorithm.get_neighbors(context.graph_view, node, direction=self.direction)
            for nbr, _ in nbrs:
                expanded.append(nbr)

        context.diagnostics.record_info("Operator", f"NeighborExpand({self.direction}) produced {len(expanded)} neighbors")
        return expanded


class EdgeFilterOperator(TraversalOperator):
    """Operator that filters edge traversals by edge type or attributes."""

    edge_type: Optional[str] = Field(None, description="Allowed edge type")

    @property
    def operator_name(self) -> str:
        return "EdgeFilter"

    def execute(
        self,
        context: TraversalExecutionContext,
        input_nodes: List[str],
        **kwargs: Any,
    ) -> List[str]:
        if not self.edge_type:
            return input_nodes

        filtered: List[str] = []
        for node in input_nodes:
            nbrs = BaseGraphAlgorithm.get_neighbors(context.graph_view, node, direction="OUTGOING")
            for nbr, edge_meta in nbrs:
                if edge_meta.get("type") == self.edge_type or edge_meta.get("label") == self.edge_type:
                    filtered.append(nbr)

        context.diagnostics.record_info("Operator", f"EdgeFilter({self.edge_type}) retained {len(filtered)} nodes")
        return filtered


class PathExpandOperator(TraversalOperator):
    """Operator that performs multi-hop path expansion up to depth limit."""

    depth: int = Field(2, description="Multi-hop depth limit")

    @property
    def operator_name(self) -> str:
        return "PathExpand"

    def execute(
        self,
        context: TraversalExecutionContext,
        input_nodes: List[str],
        **kwargs: Any,
    ) -> List[str]:
        current_frontier = list(input_nodes)
        visited = set(input_nodes)

        for _ in range(self.depth):
            next_frontier = []
            for node in current_frontier:
                nbrs = BaseGraphAlgorithm.get_neighbors(context.graph_view, node, direction="OUTGOING")
                for nbr, _ in nbrs:
                    if nbr not in visited:
                        visited.add(nbr)
                        next_frontier.append(nbr)
            current_frontier = next_frontier

        context.diagnostics.record_info("Operator", f"PathExpand(depth={self.depth}) reached {len(visited)} total nodes")
        return list(visited)


__all__ = ["NeighborExpandOperator", "EdgeFilterOperator", "PathExpandOperator"]
