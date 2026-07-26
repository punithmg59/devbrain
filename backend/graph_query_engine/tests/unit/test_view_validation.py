"""
Unit tests for GraphViewValidator and validation error handling.
"""

import pytest

from graph_query_engine.errors import ValidationError
from graph_query_engine.types import EdgeId, NodeId, RelationshipType, RepositoryId, SnapshotId
from graph_query_engine.view.builder import GraphViewBuilder
from graph_query_engine.view.edge_view import ImmutableEdgeView
from graph_query_engine.view.factory import GraphViewFactory
from graph_query_engine.view.identity import GraphIdentity
from graph_query_engine.view.metadata import GraphMetadata
from graph_query_engine.view.node_view import ImmutableNodeView
from graph_query_engine.view.snapshot import GraphSnapshotInfo
from graph_query_engine.view.validation import GraphViewValidator


def test_validator_rejects_dangling_edge():
    builder = GraphViewBuilder()
    identity = GraphIdentity(repository_id=RepositoryId("repo_x"), snapshot_id=SnapshotId("snap_x"))
    metadata = GraphMetadata(identity=identity)
    snapshot = GraphSnapshotInfo(snapshot_id=SnapshotId("snap_x"))

    n1 = ImmutableNodeView(node_id=NodeId("n1"), name="n1", qualified_name="n1", node_type="FN")
    # Edge references non-existent n2 target node
    e1 = ImmutableEdgeView(edge_id=EdgeId("e1"), source_node_id=NodeId("n1"), target_node_id=NodeId("n2_missing"), relationship_type=RelationshipType.CALLS)

    builder.set_metadata(metadata).set_snapshot(snapshot)
    builder.add_node(n1).add_edge(e1)

    unvalidated_view = builder.build()
    report = GraphViewValidator.validate(unvalidated_view)

    assert report.is_valid is False
    assert any(v.rule_name == "DANGLING_TARGET_NODE" for v in report.violations)

    with pytest.raises(ValidationError, match="GraphView validation failed"):
        GraphViewFactory.create_from_builder(builder)
