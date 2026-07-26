"""
IncomingRelationshipIndex for Fast Incoming Relationships Grouped by NodeId.
"""

from typing import Any, Iterable, Mapping
from pydantic import Field

from graph_query_engine.index.relationship_base_index import RelationshipBaseIndex
from graph_query_engine.types import EdgeId, NodeId
from graph_query_engine.view.edge_view import ImmutableEdgeView


class IncomingRelationshipIndex(RelationshipBaseIndex):
    """
    Immutable, thread-safe index grouping incoming edges by target NodeId.
    """
    incoming_map: Mapping[NodeId, tuple[ImmutableEdgeView, ...]] = Field(
        default_factory=dict,
        description="Immutable mapping of target NodeId -> tuple of incoming ImmutableEdgeView",
    )

    def incoming(self, node_id: NodeId | str) -> tuple[ImmutableEdgeView, ...]:
        """Returns tuple of incoming ImmutableEdgeView instances for node_id."""
        return self.incoming_map.get(NodeId(str(node_id)), ())

    def incoming_edges(self, node_id: NodeId | str) -> tuple[EdgeId, ...]:
        """Returns tuple of incoming EdgeIds for node_id."""
        edges = self.incoming(node_id)
        return tuple(e.edge_id for e in edges)

    def incoming_count(self, node_id: NodeId | str) -> int:
        """Returns count of incoming relationships for node_id."""
        return len(self.incoming(node_id))

    def lookup(self, key: Any) -> Iterable[ImmutableEdgeView]:
        """IGraphView lookup contract implementation."""
        return self.incoming(str(key))


__all__ = ["IncomingRelationshipIndex"]
