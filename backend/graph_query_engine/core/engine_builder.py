"""
Engine Builder Interface Placeholder.

Infrastructure placeholder only - NO business logic in Step 1.1.
"""

from typing import Protocol, Self

from graph_query_engine.config import GraphQueryEngineConfig
from graph_query_engine.core.graph_query_engine import GraphQueryEngine


class GraphQueryEngineBuilder(Protocol):
    """
    Fluent builder contract for constructing GraphQueryEngine instances.
    """

    def with_config(self, config: GraphQueryEngineConfig) -> Self:
        """Sets the engine configuration."""
        ...

    def build(self) -> GraphQueryEngine:
        """Builds and returns the configured GraphQueryEngine."""
        ...


__all__ = ["GraphQueryEngineBuilder"]
