"""
Public Query API Factory.

Factory for constructing pre-configured QueryEngine and QuerySession instances.
"""

from typing import Any, Optional
from graph_query_engine.api.context import QueryContext
from graph_query_engine.api.engine import QueryEngine
from graph_query_engine.api.executor import QueryExecutor
from graph_query_engine.api.session import QuerySession


class QueryFactory:
    """
    Factory for creating pre-configured QueryEngine and QuerySession components.
    """

    @staticmethod
    def create_engine(
        graph_view: Optional[Any] = None,
        index_layer: Optional[Any] = None,
        executor: Optional[QueryExecutor] = None,
    ) -> QueryEngine:
        """Constructs a QueryEngine instance."""
        return QueryEngine(
            executor=executor,
            graph_view=graph_view,
            index_layer=index_layer,
        )

    @staticmethod
    def create_session(
        default_context: Optional[QueryContext] = None,
        executor: Optional[QueryExecutor] = None,
    ) -> QuerySession:
        """Constructs a QuerySession instance."""
        return QuerySession(
            default_context=default_context,
            executor=executor,
        )


__all__ = ["QueryFactory"]
