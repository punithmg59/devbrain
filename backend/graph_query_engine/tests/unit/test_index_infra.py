"""
Unit tests for Index Infrastructure (BaseIndex, IndexDescriptor, IndexMetadata, IndexStatistics, IndexBuilder, IndexFactory, IndexRegistry, IndexValidator, IndexProvider, IndexLifecycle).
"""

import pytest
from pydantic import ValidationError as PydanticValidationError

from graph_query_engine.index import (
    BaseIndex,
    IndexBuilder,
    IndexDescriptor,
    IndexFactory,
    IndexLifecycle,
    IndexLifecycleState,
    IndexMetadata,
    IndexProvider,
    IndexRegistry,
    IndexStatistics,
    IndexValidator,
)
from graph_query_engine.types import NodeId, RepositoryId, SnapshotId
from graph_query_engine.view.builder import GraphViewBuilder
from graph_query_engine.view.identity import GraphIdentity
from graph_query_engine.view.metadata import GraphMetadata
from graph_query_engine.view.node_view import ImmutableNodeView
from graph_query_engine.view.snapshot import GraphSnapshotInfo


def test_index_descriptor_and_metadata_immutability():
    desc = IndexDescriptor(name="SymbolIndex", version="1.0.0")
    assert desc.name == "SymbolIndex"

    with pytest.raises((TypeError, PydanticValidationError)):
        desc.name = "MutatedIndex"  # type: ignore

    meta = IndexMetadata(source_graph_version="1.0.0")
    assert meta.source_graph_version == "1.0.0"

    with pytest.raises((TypeError, PydanticValidationError)):
        meta.source_graph_version = "2.0.0"  # type: ignore


def test_index_builder_and_factory():
    builder = GraphViewBuilder()
    identity = GraphIdentity(repository_id=RepositoryId("repo_idx"), snapshot_id=SnapshotId("snap_idx"))
    builder.set_metadata(GraphMetadata(identity=identity))
    builder.set_snapshot(GraphSnapshotInfo(snapshot_id=SnapshotId("snap_idx")))
    builder.add_node(ImmutableNodeView(node_id=NodeId("n1"), name="n1", qualified_name="n1", node_type="FN"))

    graph_view = builder.build()

    index = IndexFactory.create_index("SymbolLookupIndex", graph_view)

    assert index is not None
    assert index.index_name == "SymbolLookupIndex"
    assert index.graph_identity.repository_id == "repo_idx"
    assert index.statistics.node_count == 1


def test_index_registry_and_provider():
    registry = IndexRegistry()
    assert len(registry.list_indexes()) == 0

    builder = GraphViewBuilder()
    identity = GraphIdentity(repository_id=RepositoryId("r1"), snapshot_id=SnapshotId("s1"))
    builder.set_metadata(GraphMetadata(identity=identity))
    builder.set_snapshot(GraphSnapshotInfo(snapshot_id=SnapshotId("s1")))

    graph_view = builder.build()
    index = IndexFactory.create_index("TestIndex", graph_view)

    registry.register_instance(index)
    assert registry.has_index("TestIndex") is True
    assert len(registry.list_indexes()) == 1

    provider = IndexProvider(registry)
    resolved_index = provider.provide_index("TestIndex")
    assert resolved_index is not None
    assert resolved_index.index_name == "TestIndex"


def test_index_lifecycle_transitions():
    lifecycle = IndexLifecycle()
    assert lifecycle.current_state == IndexLifecycleState.CREATED

    lifecycle.transition_to(IndexLifecycleState.BUILDING)
    lifecycle.transition_to(IndexLifecycleState.VALIDATING)
    lifecycle.transition_to(IndexLifecycleState.READY)

    assert lifecycle.current_state == IndexLifecycleState.READY
    history = [h.state for h in lifecycle.get_history()]
    assert history == [
        IndexLifecycleState.CREATED,
        IndexLifecycleState.BUILDING,
        IndexLifecycleState.VALIDATING,
        IndexLifecycleState.READY,
    ]


def test_index_validator():
    desc = IndexDescriptor(name="ValidIndex")
    meta = IndexMetadata()
    stats = IndexStatistics()
    identity = GraphIdentity(repository_id=RepositoryId("r"), snapshot_id=SnapshotId("s"))

    index = BaseIndex(
        index_id="idx_123",
        descriptor=desc,
        metadata=meta,
        statistics=stats,
        graph_identity=identity,
    )

    report = IndexValidator.validate(index)
    assert report.is_valid is True
