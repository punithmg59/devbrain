"""
NamespaceIndex for Deterministic O(1) Lookup of Nodes by NamespaceId.
"""

from typing import Any, Iterable, Mapping, Optional
from pydantic import Field

from graph_query_engine.errors import IndexLookupError
from graph_query_engine.index.lookup_index import LookupIndex
from graph_query_engine.types import NamespaceId
from graph_query_engine.view.node_view import ImmutableNodeView


class NamespaceIndex(LookupIndex):
    """
    Immutable, thread-safe index grouping nodes by NamespaceId.
    """
    namespace_map: Mapping[NamespaceId, tuple[ImmutableNodeView, ...]] = Field(
        default_factory=dict,
        description="Immutable mapping of NamespaceId -> tuple of ImmutableNodeView",
    )

    def contains(self, namespace_id: NamespaceId | str) -> bool:
        """Returns True if namespace_id exists in the index."""
        return NamespaceId(str(namespace_id)) in self.namespace_map

    def get(self, namespace_id: NamespaceId | str) -> tuple[ImmutableNodeView, ...]:
        """
        Retrieves tuple of nodes in namespace_id. Raises IndexLookupError if missing.
        """
        nid = NamespaceId(str(namespace_id))
        nodes = self.namespace_map.get(nid)
        if nodes is None:
            raise IndexLookupError(f"NamespaceId '{namespace_id}' not found in NamespaceIndex.")
        return nodes

    def try_get(self, namespace_id: NamespaceId | str) -> Optional[tuple[ImmutableNodeView, ...]]:
        """Retrieves tuple of nodes in namespace_id or returns None."""
        return self.namespace_map.get(NamespaceId(str(namespace_id)))

    def lookup(self, key: Any) -> Iterable[ImmutableNodeView]:
        """IGraphView lookup contract implementation."""
        return self.try_get(str(key)) or ()

    def namespaces(self) -> tuple[NamespaceId, ...]:
        """Returns tuple of all indexed NamespaceIds."""
        return tuple(self.namespace_map.keys())

    def count(self) -> int:
        """Returns the total number of indexed namespaces."""
        return len(self.namespace_map)


__all__ = ["NamespaceIndex"]
