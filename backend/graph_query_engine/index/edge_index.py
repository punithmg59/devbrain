"""
EdgeIndex for Deterministic O(1) Lookup by EdgeId.
"""

from typing import Any, Iterable, Mapping, Optional
from pydantic import Field

from graph_query_engine.errors import IndexLookupError
from graph_query_engine.index.lookup_index import LookupIndex
from graph_query_engine.types import EdgeId
from graph_query_engine.view.edge_view import ImmutableEdgeView


class EdgeIndex(LookupIndex):
    """
    Immutable, thread-safe index providing O(1) lookups over relationship edges by EdgeId.
    """
    edge_map: Mapping[EdgeId, ImmutableEdgeView] = Field(
        default_factory=dict,
        description="Immutable mapping of EdgeId -> ImmutableEdgeView",
    )

    def contains(self, edge_id: EdgeId | str) -> bool:
        """Returns True if edge_id exists in the index."""
        return EdgeId(str(edge_id)) in self.edge_map

    def exists(self, edge_id: EdgeId | str) -> bool:
        """Alias for contains()."""
        return self.contains(edge_id)

    def get(self, edge_id: EdgeId | str) -> ImmutableEdgeView:
        """
        Retrieves ImmutableEdgeView by EdgeId. Raises IndexLookupError if missing.
        """
        eid = EdgeId(str(edge_id))
        edge = self.edge_map.get(eid)
        if edge is None:
            raise IndexLookupError(f"EdgeId '{edge_id}' not found in EdgeIndex.")
        return edge

    def try_get(self, edge_id: EdgeId | str) -> Optional[ImmutableEdgeView]:
        """Retrieves ImmutableEdgeView by EdgeId or returns None."""
        return self.edge_map.get(EdgeId(str(edge_id)))

    def lookup(self, key: Any) -> Iterable[ImmutableEdgeView]:
        """IGraphView lookup contract implementation."""
        res = self.try_get(str(key))
        return (res,) if res is not None else ()

    def size(self) -> int:
        """Returns the total number of indexed edges."""
        return len(self.edge_map)

    def keys(self) -> tuple[EdgeId, ...]:
        """Returns tuple of all indexed EdgeIds."""
        return tuple(self.edge_map.keys())

    def values(self) -> tuple[ImmutableEdgeView, ...]:
        """Returns tuple of all indexed ImmutableEdgeView instances."""
        return tuple(self.edge_map.values())


__all__ = ["EdgeIndex"]
