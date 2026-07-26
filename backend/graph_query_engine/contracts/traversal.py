"""
Traversal Strategy Interface Contracts.

CONTRACT ONLY - DO NOT IMPLEMENT IN STEP 1.1.
"""

from typing import Any, Iterable, Protocol

from graph_query_engine.types import NodeId


class ITraversalStrategy(Protocol):
    """
    Contract for graph traversal algorithms (e.g. BFS, DFS, Shortest Path).
    """

    def traverse(
        self,
        start_node: NodeId,
        graph_view: Any,
        max_depth: int,
    ) -> Iterable[NodeId]:
        """Executes traversal strategy starting from start_node."""
        ...


class ITraversalRegistry(Protocol):
    """
    Registry for managing available traversal strategy implementations.
    """

    def get_strategy(self, name: str) -> ITraversalStrategy:
        """Retrieves a traversal strategy by algorithm name."""
        ...


__all__ = ["ITraversalStrategy", "ITraversalRegistry"]
