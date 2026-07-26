"""
CSRAdjacencyIndex - Outgoing Adjacency using Compressed Sparse Row (CSR) Layout.
"""

from typing import Any, Iterable, Mapping
from pydantic import Field

from graph_query_engine.index.relationship_base_index import RelationshipBaseIndex
from graph_query_engine.types import EdgeId, NodeId


class CSRAdjacencyIndex(RelationshipBaseIndex):
    """
    Immutable, thread-safe CSR index for O(1) outgoing edge offset lookups.
    """
    node_offsets: tuple[int, ...] = Field(
        default_factory=tuple,
        description="CSR offset array mapping node index to target_nodes slice",
    )
    node_id_map: Mapping[NodeId, int] = Field(
        default_factory=dict,
        description="Immutable mapping of NodeId -> integer node index",
    )
    target_nodes: tuple[NodeId, ...] = Field(
        default_factory=tuple,
        description="Contiguous array of target NodeIds",
    )
    edge_ids: tuple[EdgeId, ...] = Field(
        default_factory=tuple,
        description="Contiguous array of EdgeIds corresponding to target_nodes",
    )

    def contains(self, node_id: NodeId | str) -> bool:
        """Returns True if node_id exists in the CSR node_id_map."""
        return NodeId(str(node_id)) in self.node_id_map

    def neighbors(self, node_id: NodeId | str) -> tuple[NodeId, ...]:
        """Returns tuple of outgoing target NodeIds for node_id."""
        nid = NodeId(str(node_id))
        idx = self.node_id_map.get(nid)
        if idx is None or idx >= len(self.node_offsets) - 1:
            return ()
        start = self.node_offsets[idx]
        end = self.node_offsets[idx + 1]
        return self.target_nodes[start:end]

    def edge_ids_for(self, node_id: NodeId | str) -> tuple[EdgeId, ...]:
        """Returns tuple of outgoing EdgeIds for node_id."""
        nid = NodeId(str(node_id))
        idx = self.node_id_map.get(nid)
        if idx is None or idx >= len(self.node_offsets) - 1:
            return ()
        start = self.node_offsets[idx]
        end = self.node_offsets[idx + 1]
        return self.edge_ids[start:end]

    def degree(self, node_id: NodeId | str) -> int:
        """Returns outgoing degree of node_id."""
        nid = NodeId(str(node_id))
        idx = self.node_id_map.get(nid)
        if idx is None or idx >= len(self.node_offsets) - 1:
            return 0
        return self.node_offsets[idx + 1] - self.node_offsets[idx]

    def lookup(self, key: Any) -> Iterable[NodeId]:
        """IGraphView lookup contract implementation."""
        return self.neighbors(str(key))

    def size(self) -> int:
        """Returns total number of indexed nodes."""
        return len(self.node_id_map)


__all__ = ["CSRAdjacencyIndex"]
