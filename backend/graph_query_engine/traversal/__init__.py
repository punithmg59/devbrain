"""
Graph Traversal Package (Contracts Only).
"""

from graph_query_engine.traversal.contracts import (
    ITraversalRegistry,
    ITraversalStrategy,
)

__all__ = ["ITraversalStrategy", "ITraversalRegistry"]
