"""
OutgoingRelationshipIndex for Fast Outgoing Relationships Grouped by NodeId.
"""

from typing import Any, Iterable, Mapping
from pydantic import Field

from graph_query_engine.index.relationship_base_index import RelationshipBaseIndex
from graph_query_engine.types import EdgeId, NodeId
from graph_query_engine.view.edge_view import ImmutableEdgeView


class OutgoingRelationshipIndex(RelationshipBaseIndex):
    """
    Immutable, thread-safe index grouping outgoing edges by source NodeId.
    """
    outgoing_map: Mapping[NodeId, tuple[ImmutableEdgeView, ...]] = Field(
        default_factory=dict,
        description="Immutable mapping of source NodeId -> tuple of outgoing ImmutableEdgeView",
    )

    def outgoing(self, node_id: NodeId | str) -> tuple[ImmutableEdgeView, ...]:
        """Returns tuple of outgoing ImmutableEdgeView instances for node_id."""
        return self.outgoing_map.get(NodeId(str(node_id)), ())

    def outgoing_edges(self, node_id: NodeId | str) -> tuple[EdgeId, ...]:
        """Returns tuple of outgoing EdgeIds for node_id."""
        edges = self.outgoing(node_id)
        return tuple(e.edge_id for e in edges)

    def outgoing_count(self, node_id: NodeId | str) -> int:
        """Returns count of outgoing relationships for node_id."""
        return len(self.outgoing(node_id))

    def lookup(self, key: Any) -> Iterable[ImmutableEdgeView]:
        """IGraphView lookup contract implementation."""
        return self.outgoing(str(key))


__all__ = ["OutgoingRelationshipIndex"]
