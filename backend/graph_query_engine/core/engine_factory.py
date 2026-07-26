"""
Engine Factory Interface Placeholder.

Infrastructure placeholder only - NO business logic in Step 1.1.
"""

from typing import Protocol

from graph_query_engine.config import GraphQueryEngineConfig
from graph_query_engine.core.graph_query_engine import GraphQueryEngine


class GraphQueryEngineFactory(Protocol):
    """
    Contract for manufacturing configured GraphQueryEngine instances.
    """

    def create_engine(
        self,
        config: GraphQueryEngineConfig,
    ) -> GraphQueryEngine:
        """Constructs a new GraphQueryEngine instance."""
        ...


__all__ = ["GraphQueryEngineFactory"]
