"""
Graph View Contract.

CONTRACT ONLY - DO NOT IMPLEMENT IN STEP 1.1.
Future implementation: Step 2 (GraphView & Storage Read Adapter).
"""

from typing import Any, Iterable, Optional, Protocol

from graph_query_engine.types import EdgeId, NodeId, RelationshipType, SnapshotId


class IGraphView(Protocol):
    """
    Contract for accessing an immutable graph snapshot read interface.
    """

    @property
    def snapshot_id(self) -> SnapshotId:
        """Returns the immutable snapshot identifier."""
        ...

    def get_node(self, node_id: NodeId) -> Optional[dict[str, Any]]:
        """Retrieves node record by NodeId."""
        ...

    def get_neighbors(
        self,
        node_id: NodeId,
        relationship_type: Optional[RelationshipType] = None,
    ) -> Iterable[NodeId]:
        """Retrieves neighboring NodeIds connected to node_id."""
        ...

    def get_edge(self, edge_id: EdgeId) -> Optional[dict[str, Any]]:
        """Retrieves edge record by EdgeId."""
        ...


__all__ = ["IGraphView"]
