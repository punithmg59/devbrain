"""
Unit tests for GraphViewLifecycle state machine.
"""

from graph_query_engine.types import NodeId, RepositoryId, SnapshotId
from graph_query_engine.view.builder import GraphViewBuilder
from graph_query_engine.view.factory import GraphViewFactory
from graph_query_engine.view.identity import GraphIdentity
from graph_query_engine.view.lifecycle import (
    GraphViewLifecycle,
    GraphViewLifecycleState,
)
from graph_query_engine.view.metadata import GraphMetadata
from graph_query_engine.view.node_view import ImmutableNodeView
from graph_query_engine.view.snapshot import GraphSnapshotInfo


def test_view_lifecycle_transitions():
    lifecycle = GraphViewLifecycle()
    assert lifecycle.current_state == GraphViewLifecycleState.CREATED

    builder = GraphViewBuilder()
    identity = GraphIdentity(repository_id=RepositoryId("r1"), snapshot_id=SnapshotId("s1"))
    builder.set_metadata(GraphMetadata(identity=identity))
    builder.set_snapshot(GraphSnapshotInfo(snapshot_id=SnapshotId("s1")))
    builder.add_node(ImmutableNodeView(node_id=NodeId("n1"), name="n1", qualified_name="n1", node_type="FN"))

    view = GraphViewFactory.create_from_builder(builder, lifecycle=lifecycle)

    assert view is not None
    assert lifecycle.current_state == GraphViewLifecycleState.READY

    history = lifecycle.get_history()
    states = [h.state for h in history]
    assert states == [
        GraphViewLifecycleState.CREATED,
        GraphViewLifecycleState.BUILDING,
        GraphViewLifecycleState.VALIDATING,
        GraphViewLifecycleState.READY,
    ]
