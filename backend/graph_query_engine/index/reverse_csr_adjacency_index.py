"""
ReverseCSRAdjacencyIndex - Incoming Adjacency using Reverse CSR Layout.
"""

from typing import Any, Iterable, Mapping
from pydantic import Field

from graph_query_engine.index.relationship_base_index import RelationshipBaseIndex
from graph_query_engine.types import EdgeId, NodeId


class ReverseCSRAdjacencyIndex(RelationshipBaseIndex):
    """
    Immutable, thread-safe Reverse CSR index for O(1) incoming edge offset lookups.
    """
    node_offsets: tuple[int, ...] = Field(
        default_factory=tuple,
        description="CSR offset array mapping node index to source_nodes slice",
    )
    node_id_map: Mapping[NodeId, int] = Field(
        default_factory=dict,
        description="Immutable mapping of NodeId -> integer node index",
    )
    source_nodes: tuple[NodeId, ...] = Field(
        default_factory=tuple,
        description="Contiguous array of source NodeIds",
    )
    edge_ids: tuple[EdgeId, ...] = Field(
        default_factory=tuple,
        description="Contiguous array of EdgeIds corresponding to source_nodes",
    )

    def contains(self, node_id: NodeId | str) -> bool:
        """Returns True if node_id exists in the Reverse CSR node_id_map."""
        return NodeId(str(node_id)) in self.node_id_map

    def incoming_neighbors(self, node_id: NodeId | str) -> tuple[NodeId, ...]:
        """Returns tuple of incoming source NodeIds for node_id."""
        nid = NodeId(str(node_id))
        idx = self.node_id_map.get(nid)
        if idx is None or idx >= len(self.node_offsets) - 1:
            return ()
        start = self.node_offsets[idx]
        end = self.node_offsets[idx + 1]
        return self.source_nodes[start:end]

    def incoming_edges(self, node_id: NodeId | str) -> tuple[EdgeId, ...]:
        """Returns tuple of incoming EdgeIds for node_id."""
        nid = NodeId(str(node_id))
        idx = self.node_id_map.get(nid)
        if idx is None or idx >= len(self.node_offsets) - 1:
            return ()
        start = self.node_offsets[idx]
        end = self.node_offsets[idx + 1]
        return self.edge_ids[start:end]

    def in_degree(self, node_id: NodeId | str) -> int:
        """Returns incoming in_degree of node_id."""
        nid = NodeId(str(node_id))
        idx = self.node_id_map.get(nid)
        if idx is None or idx >= len(self.node_offsets) - 1:
            return 0
        return self.node_offsets[idx + 1] - self.node_offsets[idx]

    def lookup(self, key: Any) -> Iterable[NodeId]:
        """IGraphView lookup contract implementation."""
        return self.incoming_neighbors(str(key))


__all__ = ["ReverseCSRAdjacencyIndex"]
