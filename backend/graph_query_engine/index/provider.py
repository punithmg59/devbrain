"""
IndexProvider for Dependency Injecting Index Instances.
"""

from typing import Optional

from graph_query_engine.index.base import BaseIndex
from graph_query_engine.index.registry import IndexRegistry


class IndexProvider:
    """
    Provider exposing resolved index instances from an IndexRegistry.
    """

    def __init__(self, registry: IndexRegistry) -> None:
        self._registry = registry

    def provide_index(self, index_name: str) -> Optional[BaseIndex]:
        """
        Retrieves the requested index instance from registry.
        """
        return self._registry.get_index(index_name)

    def has_index(self, index_name: str) -> bool:
        """Checks if index is provided by registry."""
        return self._registry.has_index(index_name)


__all__ = ["IndexProvider"]
