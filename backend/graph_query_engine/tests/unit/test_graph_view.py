"""
Unit tests for GraphView, GraphIdentity, ImmutableNodeView, ImmutableEdgeView, and Immutability.
"""

import pytest
from pydantic import ValidationError as PydanticValidationError

from graph_query_engine.types import (
    EdgeId,
    NodeId,
    RelationshipType,
    RepositoryId,
    SnapshotId,
)
from graph_query_engine.view.builder import GraphViewBuilder
from graph_query_engine.view.edge_view import ImmutableEdgeView
from graph_query_engine.view.identity import GraphIdentity
from graph_query_engine.view.metadata import GraphMetadata
from graph_query_engine.view.node_view import ImmutableNodeView
from graph_query_engine.view.snapshot import GraphSnapshotInfo


def test_graph_identity_creation():
    identity = GraphIdentity(
        repository_id=RepositoryId("repo_1"),
        snapshot_id=SnapshotId("snap_1"),
        graph_version="1.0.0",
    )
    assert identity.repository_id == "repo_1"
    assert identity.snapshot_id == "snap_1"
    assert identity.graph_version == "1.0.0"

    with pytest.raises((TypeError, PydanticValidationError)):
        identity.graph_version = "2.0.0"  # type: ignore


def test_graph_metadata_delegation():
    identity = GraphIdentity(
        repository_id=RepositoryId("repo_10"),
        snapshot_id=SnapshotId("snap_10"),
        graph_version="2.1.0",
    )
    metadata = GraphMetadata(identity=identity)

    assert metadata.repository_id == "repo_10"
    assert metadata.snapshot_id == "snap_10"
    assert metadata.graph_version == "2.1.0"


def test_graph_view_neighbor_lookup():
    builder = GraphViewBuilder()
    identity = GraphIdentity(
        repository_id=RepositoryId("repo_1"),
        snapshot_id=SnapshotId("snap_1"),
    )
    metadata = GraphMetadata(identity=identity)
    snapshot = GraphSnapshotInfo(snapshot_id=SnapshotId("snap_1"))

    n1 = ImmutableNodeView(node_id=NodeId("n1"), name="n1", qualified_name="n1", node_type="FN")
    n2 = ImmutableNodeView(node_id=NodeId("n2"), name="n2", qualified_name="n2", node_type="FN")
    n3 = ImmutableNodeView(node_id=NodeId("n3"), name="n3", qualified_name="n3", node_type="FN")

    e1 = ImmutableEdgeView(edge_id=EdgeId("e1"), source_node_id=NodeId("n1"), target_node_id=NodeId("n2"), relationship_type=RelationshipType.CALLS)
    e2 = ImmutableEdgeView(edge_id=EdgeId("e2"), source_node_id=NodeId("n1"), target_node_id=NodeId("n3"), relationship_type=RelationshipType.IMPORTS)

    builder.set_metadata(metadata).set_snapshot(snapshot)
    builder.add_nodes([n1, n2, n3]).add_edges([e1, e2])

    view = builder.build()

    all_neighbors = list(view.get_neighbors(NodeId("n1")))
    assert set(all_neighbors) == {"n2", "n3"}

    calls_neighbors = list(view.get_neighbors(NodeId("n1"), RelationshipType.CALLS))
    assert calls_neighbors == ["n2"]


def test_graph_view_immutability():
    identity = GraphIdentity(repository_id=RepositoryId("r1"), snapshot_id=SnapshotId("s1"))
    metadata = GraphMetadata(identity=identity)
    builder = GraphViewBuilder()
    builder.set_metadata(metadata)
    builder.set_snapshot(GraphSnapshotInfo(snapshot_id=SnapshotId("s1")))
    view = builder.build()

    with pytest.raises((TypeError, PydanticValidationError)):
        view.metadata = None  # type: ignore
