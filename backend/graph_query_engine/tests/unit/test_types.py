"""
Unit tests for Shared Primitive Types.
"""

from graph_query_engine.types import (
    DependencyType,
    EdgeId,
    FileId,
    NodeId,
    RelationshipType,
    SnapshotId,
    TraversalDirection,
)


def test_primitive_types():
    node_id = NodeId("node_123")
    edge_id = EdgeId("edge_456")
    file_id = FileId("file_789")
    snapshot_id = SnapshotId("snap_abc")

    assert str(node_id) == "node_123"
    assert str(edge_id) == "edge_456"
    assert str(file_id) == "file_789"
    assert str(snapshot_id) == "snap_abc"


def test_enum_types():
    assert TraversalDirection.INBOUND == "INBOUND"
    assert TraversalDirection.OUTBOUND == "OUTBOUND"
    assert TraversalDirection.BOTH == "BOTH"

    assert RelationshipType.CALLS == "CALLS"
    assert RelationshipType.INHERITS == "INHERITS"

    assert DependencyType.DIRECT == "DIRECT"
    assert DependencyType.TRANSITIVE == "TRANSITIVE"
