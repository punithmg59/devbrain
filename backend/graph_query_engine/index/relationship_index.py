"""
RelationshipIndex for Fast Edge Lookup by EdgeId.
"""

from typing import Any, Iterable, Mapping, Optional
from pydantic import Field

from graph_query_engine.errors import RelationshipLookupError
from graph_query_engine.index.relationship_base_index import RelationshipBaseIndex
from graph_query_engine.types import EdgeId
from graph_query_engine.view.edge_view import ImmutableEdgeView


class RelationshipIndex(RelationshipBaseIndex):
    """
    Immutable, thread-safe index for edge lookup by relationship EdgeId.
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
        Retrieves ImmutableEdgeView by EdgeId. Raises RelationshipLookupError if missing.
        """
        eid = EdgeId(str(edge_id))
        edge = self.edge_map.get(eid)
        if edge is None:
            raise RelationshipLookupError(f"EdgeId '{edge_id}' not found in RelationshipIndex.")
        return edge

    def try_get(self, edge_id: EdgeId | str) -> Optional[ImmutableEdgeView]:
        """Retrieves ImmutableEdgeView by EdgeId or returns None."""
        return self.edge_map.get(EdgeId(str(edge_id)))

    def lookup(self, key: Any) -> Iterable[ImmutableEdgeView]:
        """IGraphView lookup contract implementation."""
        res = self.try_get(str(key))
        return (res,) if res is not None else ()

    def enumeration(self) -> tuple[ImmutableEdgeView, ...]:
        """Returns tuple of all indexed relationship edge views."""
        return tuple(self.edge_map.values())


__all__ = ["RelationshipIndex"]
