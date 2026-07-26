"""
Immutable Thread-Safe GraphView Implementation.

Implements IGraphView contract from graph_query_engine.contracts.view.
"""

from typing import Any, Iterable, Mapping, Optional
from pydantic import BaseModel, ConfigDict, Field

from graph_query_engine.contracts.view import IGraphView
from graph_query_engine.types import (
    EdgeId,
    NodeId,
    RelationshipType,
    RepositoryId,
    SnapshotId,
)
from graph_query_engine.view.edge_view import ImmutableEdgeView
from graph_query_engine.view.metadata import GraphMetadata
from graph_query_engine.view.node_view import ImmutableNodeView
from graph_query_engine.view.snapshot import GraphSnapshotInfo
from graph_query_engine.view.statistics import GraphStatistics


class GraphView(BaseModel):
    """
    Immutable, read-only, thread-safe GraphView.

    Implements the IGraphView protocol for deterministic access over graph snapshots.
    """
    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    metadata: GraphMetadata = Field(..., description="Graph metadata")
    snapshot: GraphSnapshotInfo = Field(..., description="Graph snapshot information")
    statistics: GraphStatistics = Field(..., description="Structural graph statistics")
    node_map: Mapping[NodeId, ImmutableNodeView] = Field(
        default_factory=dict,
        description="Immutable mapping of NodeId -> ImmutableNodeView",
    )
    edge_map: Mapping[EdgeId, ImmutableEdgeView] = Field(
        default_factory=dict,
        description="Immutable mapping of EdgeId -> ImmutableEdgeView",
    )
    outgoing_adjacency: Mapping[NodeId, tuple[EdgeId, ...]] = Field(
        default_factory=dict,
        description="Immutable outgoing edge adjacency map",
    )
    incoming_adjacency: Mapping[NodeId, tuple[EdgeId, ...]] = Field(
        default_factory=dict,
        description="Immutable incoming edge adjacency map",
    )

    @property
    def snapshot_id(self) -> SnapshotId:
        """Returns the immutable snapshot identifier."""
        return self.snapshot.snapshot_id

    @property
    def repository_id(self) -> RepositoryId:
        """Returns the repository identifier."""
        return self.metadata.repository_id

    @property
    def schema_version(self) -> str:
        """Returns schema version string."""
        return self.metadata.schema_version

    @property
    def nodes(self) -> Mapping[NodeId, ImmutableNodeView]:
        """Exposes read-only mapping of nodes."""
        return self.node_map

    @property
    def edges(self) -> Mapping[EdgeId, ImmutableEdgeView]:
        """Exposes read-only mapping of edges."""
        return self.edge_map

    def get_node_view(self, node_id: NodeId) -> Optional[ImmutableNodeView]:
        """Retrieves ImmutableNodeView by NodeId in O(1) time."""
        return self.node_map.get(node_id)

    def get_node(self, node_id: NodeId) -> Optional[dict[str, Any]]:
        """
        Retrieves node dictionary representation by NodeId (IGraphView contract).
        """
        node_view = self.get_node_view(node_id)
        return node_view.model_dump() if node_view is not None else None

    def get_edge_view(self, edge_id: EdgeId) -> Optional[ImmutableEdgeView]:
        """Retrieves ImmutableEdgeView by EdgeId in O(1) time."""
        return self.edge_map.get(edge_id)

    def get_edge(self, edge_id: EdgeId) -> Optional[dict[str, Any]]:
        """
        Retrieves edge dictionary representation by EdgeId (IGraphView contract).
        """
        edge_view = self.get_edge_view(edge_id)
        return edge_view.model_dump() if edge_view is not None else None

    def get_neighbors(
        self,
        node_id: NodeId,
        relationship_type: Optional[RelationshipType] = None,
    ) -> Iterable[NodeId]:
        """
        Retrieves neighboring NodeIds connected to node_id via outgoing edges (IGraphView contract).
        """
        outgoing_edge_ids = self.outgoing_adjacency.get(node_id, ())
        neighbors: list[NodeId] = []

        for edge_id in outgoing_edge_ids:
            edge = self.edge_map.get(edge_id)
            if edge is not None:
                if relationship_type is None or edge.relationship_type == relationship_type:
                    neighbors.append(edge.target_node_id)

        return tuple(neighbors)


__all__ = ["GraphView"]
