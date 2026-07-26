"""
SelfLoopIndex for Identifying Edges Whose Source Equals Target NodeId.
"""

from typing import Any, Iterable, Mapping
from pydantic import Field

from graph_query_engine.index.relationship_base_index import RelationshipBaseIndex
from graph_query_engine.types import NodeId
from graph_query_engine.view.edge_view import ImmutableEdgeView


class SelfLoopIndex(RelationshipBaseIndex):
    """
    Immutable, thread-safe index tracking self-referential edges (source_node_id == target_node_id).
    """
    loop_map: Mapping[NodeId, tuple[ImmutableEdgeView, ...]] = Field(
        default_factory=dict,
        description="Immutable mapping of NodeId -> tuple of self-loop ImmutableEdgeView",
    )

    def contains(self, node_id: NodeId | str) -> bool:
        """Returns True if node_id has at least one self-loop edge."""
        return NodeId(str(node_id)) in self.loop_map

    def self_loops(self, node_id: NodeId | str) -> tuple[ImmutableEdgeView, ...]:
        """Returns tuple of self-loop ImmutableEdgeView instances for node_id."""
        return self.loop_map.get(NodeId(str(node_id)), ())

    def count(self) -> int:
        """Returns total number of self-loop edges indexed across all nodes."""
        return sum(len(v) for v in self.loop_map.values())

    def lookup(self, key: Any) -> Iterable[ImmutableEdgeView]:
        """IGraphView lookup contract implementation."""
        return self.self_loops(str(key))


__all__ = ["SelfLoopIndex"]
