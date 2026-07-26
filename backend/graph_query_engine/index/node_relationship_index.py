"""
NodeRelationshipIndex for Retrieving Every Relationship Attached to a Node.
"""

from typing import Any, Iterable, Mapping
from pydantic import Field

from graph_query_engine.index.relationship_base_index import RelationshipBaseIndex
from graph_query_engine.types import NodeId
from graph_query_engine.view.edge_view import ImmutableEdgeView


class NodeRelationshipIndex(RelationshipBaseIndex):
    """
    Immutable, thread-safe index grouping all edges (incoming + outgoing) by NodeId.
    """
    relationship_map: Mapping[NodeId, tuple[ImmutableEdgeView, ...]] = Field(
        default_factory=dict,
        description="Immutable mapping of NodeId -> tuple of attached ImmutableEdgeView",
    )

    def relationships(self, node_id: NodeId | str) -> tuple[ImmutableEdgeView, ...]:
        """Returns tuple of all ImmutableEdgeView instances attached to node_id."""
        return self.relationship_map.get(NodeId(str(node_id)), ())

    def relationship_count(self, node_id: NodeId | str) -> int:
        """Returns count of all attached relationships for node_id."""
        return len(self.relationships(node_id))

    def lookup(self, key: Any) -> Iterable[ImmutableEdgeView]:
        """IGraphView lookup contract implementation."""
        return self.relationships(str(key))


__all__ = ["NodeRelationshipIndex"]
