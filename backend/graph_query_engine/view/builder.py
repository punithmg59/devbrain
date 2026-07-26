"""
GraphView Builder for Constructing Immutable Graph Views.
"""

from typing import Iterable, Mapping, Self

from graph_query_engine.types import EdgeId, NodeId
from graph_query_engine.view.edge_view import ImmutableEdgeView
from graph_query_engine.view.graph_view import GraphView
from graph_query_engine.view.metadata import GraphMetadata
from graph_query_engine.view.node_view import ImmutableNodeView
from graph_query_engine.view.snapshot import GraphSnapshotInfo
from graph_query_engine.view.statistics import GraphStatistics


class GraphViewBuilder:
    """
    Builder for assembling ImmutableNodeView, ImmutableEdgeView, Metadata, Snapshot, and Statistics into GraphView.
    """

    def __init__(self) -> None:
        self._nodes: dict[NodeId, ImmutableNodeView] = {}
        self._edges: dict[EdgeId, ImmutableEdgeView] = {}
        self._outgoing_adjacency: dict[NodeId, list[EdgeId]] = {}
        self._incoming_adjacency: dict[NodeId, list[EdgeId]] = {}
        self._metadata: GraphMetadata | None = None
        self._snapshot: GraphSnapshotInfo | None = None
        self._statistics: GraphStatistics | None = None

    def set_metadata(self, metadata: GraphMetadata) -> Self:
        """Sets graph metadata."""
        self._metadata = metadata
        return self

    def set_snapshot(self, snapshot: GraphSnapshotInfo) -> Self:
        """Sets snapshot information."""
        self._snapshot = snapshot
        return self

    def set_statistics(self, statistics: GraphStatistics) -> Self:
        """Sets graph statistics."""
        self._statistics = statistics
        return self

    def add_node(self, node_view: ImmutableNodeView) -> Self:
        """Adds an ImmutableNodeView to graph builder."""
        self._nodes[node_view.node_id] = node_view
        if node_view.node_id not in self._outgoing_adjacency:
            self._outgoing_adjacency[node_view.node_id] = []
        if node_view.node_id not in self._incoming_adjacency:
            self._incoming_adjacency[node_view.node_id] = []
        return self

    def add_nodes(self, node_views: Iterable[ImmutableNodeView]) -> Self:
        """Adds multiple ImmutableNodeView instances."""
        for nv in node_views:
            self.add_node(nv)
        return self

    def add_edge(self, edge_view: ImmutableEdgeView) -> Self:
        """Adds an ImmutableEdgeView and updates adjacency lists."""
        self._edges[edge_view.edge_id] = edge_view

        src = edge_view.source_node_id
        tgt = edge_view.target_node_id

        if src not in self._outgoing_adjacency:
            self._outgoing_adjacency[src] = []
        self._outgoing_adjacency[src].append(edge_view.edge_id)

        if tgt not in self._incoming_adjacency:
            self._incoming_adjacency[tgt] = []
        self._incoming_adjacency[tgt].append(edge_view.edge_id)

        return self

    def add_edges(self, edge_views: Iterable[ImmutableEdgeView]) -> Self:
        """Adds multiple ImmutableEdgeView instances."""
        for ev in edge_views:
            self.add_edge(ev)
        return self

    def build(self) -> GraphView:
        """
        Constructs and returns an unvalidated GraphView instance.
        """
        if self._metadata is None:
            raise ValueError("GraphMetadata must be set before building GraphView.")
        if self._snapshot is None:
            raise ValueError("GraphSnapshotInfo must be set before building GraphView.")

        # Compute default statistics if not explicitly set
        stats = self._statistics or GraphStatistics(
            node_count=len(self._nodes),
            edge_count=len(self._edges),
        )

        outgoing_adj = {k: tuple(v) for k, v in self._outgoing_adjacency.items()}
        incoming_adj = {k: tuple(v) for k, v in self._incoming_adjacency.items()}

        return GraphView(
            metadata=self._metadata,
            snapshot=self._snapshot,
            statistics=stats,
            node_map=dict(self._nodes),
            edge_map=dict(self._edges),
            outgoing_adjacency=outgoing_adj,
            incoming_adjacency=incoming_adj,
        )


__all__ = ["GraphViewBuilder"]
