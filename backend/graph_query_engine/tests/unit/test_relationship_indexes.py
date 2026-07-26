"""
Comprehensive unit test suite for Relationship Indexes (CSRAdjacencyIndex, ReverseCSRAdjacencyIndex, RelationshipIndex, OutgoingRelationshipIndex, IncomingRelationshipIndex, NodeRelationshipIndex, RelationshipTypeIndex, SelfLoopIndex).
"""

from concurrent.futures import ThreadPoolExecutor
import pytest

from graph_query_engine.errors import DanglingEdgeError, RelationshipLookupError
from graph_query_engine.index import (
    CSRAdjacencyIndex,
    IncomingRelationshipIndex,
    IndexBuilder,
    IndexFactory,
    IndexRegistry,
    NodeRelationshipIndex,
    OutgoingRelationshipIndex,
    RelationshipIndex,
    RelationshipTypeIndex,
    ReverseCSRAdjacencyIndex,
    SelfLoopIndex,
)
from graph_query_engine.types import (
    EdgeId,
    FileId,
    NodeId,
    RelationshipType,
    RepositoryId,
    SnapshotId,
)
from graph_query_engine.view.builder import GraphViewBuilder
from graph_query_engine.view.edge_view import ImmutableEdgeView
from graph_query_engine.view.factory import GraphViewFactory
from graph_query_engine.view.identity import GraphIdentity
from graph_query_engine.view.metadata import GraphMetadata
from graph_query_engine.view.node_view import ImmutableNodeView
from graph_query_engine.view.snapshot import GraphSnapshotInfo


@pytest.fixture
def relationship_graph_view():
    builder = GraphViewBuilder()
    identity = GraphIdentity(repository_id=RepositoryId("repo_rel"), snapshot_id=SnapshotId("snap_rel"))
    builder.set_metadata(GraphMetadata(identity=identity))
    builder.set_snapshot(GraphSnapshotInfo(snapshot_id=SnapshotId("snap_rel")))

    n1 = ImmutableNodeView(node_id=NodeId("n1"), name="n1", qualified_name="n1", node_type="FN", file=FileId("a.py"))
    n2 = ImmutableNodeView(node_id=NodeId("n2"), name="n2", qualified_name="n2", node_type="FN", file=FileId("b.py"))
    n3 = ImmutableNodeView(node_id=NodeId("n3"), name="n3", qualified_name="n3", node_type="FN", file=FileId("c.py"))

    e1 = ImmutableEdgeView(edge_id=EdgeId("e1"), source_node_id=NodeId("n1"), target_node_id=NodeId("n2"), relationship_type=RelationshipType.CALLS)
    e2 = ImmutableEdgeView(edge_id=EdgeId("e2"), source_node_id=NodeId("n1"), target_node_id=NodeId("n3"), relationship_type=RelationshipType.IMPORTS)
    e3 = ImmutableEdgeView(edge_id=EdgeId("e3"), source_node_id=NodeId("n2"), target_node_id=NodeId("n3"), relationship_type=RelationshipType.CALLS)
    e4_self = ImmutableEdgeView(edge_id=EdgeId("e4"), source_node_id=NodeId("n3"), target_node_id=NodeId("n3"), relationship_type=RelationshipType.USES)

    builder.add_nodes([n1, n2, n3]).add_edges([e1, e2, e3, e4_self])
    return builder.build()


def test_csr_adjacency_index(relationship_graph_view):
    builder = IndexBuilder()
    csr = builder.build_csr_adjacency_index(relationship_graph_view)

    assert csr.contains("n1") is True
    assert set(csr.neighbors("n1")) == {"n2", "n3"}
    assert csr.degree("n1") == 2

    assert csr.neighbors("n3") == ("n3",)
    assert csr.degree("n3") == 1


def test_reverse_csr_adjacency_index(relationship_graph_view):
    builder = IndexBuilder()
    rcsr = builder.build_reverse_csr_adjacency_index(relationship_graph_view)

    assert rcsr.contains("n3") is True
    assert set(rcsr.incoming_neighbors("n3")) == {"n1", "n2", "n3"}
    assert rcsr.in_degree("n3") == 3


def test_relationship_index(relationship_graph_view):
    builder = IndexBuilder()
    rel = builder.build_relationship_index(relationship_graph_view)

    assert rel.contains("e1") is True
    e1 = rel.get("e1")
    assert e1.relationship_type == RelationshipType.CALLS

    with pytest.raises(RelationshipLookupError):
        rel.get("e999")


def test_outgoing_and_incoming_relationship_indexes(relationship_graph_view):
    builder = IndexBuilder()
    out_idx = builder.build_outgoing_relationship_index(relationship_graph_view)
    in_idx = builder.build_incoming_relationship_index(relationship_graph_view)

    assert out_idx.outgoing_count("n1") == 2
    assert in_idx.incoming_count("n3") == 3


def test_node_relationship_index(relationship_graph_view):
    builder = IndexBuilder()
    node_rel = builder.build_node_relationship_index(relationship_graph_view)

    # n1 has e1(out), e2(out)
    assert node_rel.relationship_count("n1") == 2
    # n2 has e1(in), e3(out)
    assert node_rel.relationship_count("n2") == 2


def test_relationship_type_index(relationship_graph_view):
    builder = IndexBuilder()
    rel_type = builder.build_relationship_type_index(relationship_graph_view)

    assert rel_type.count(RelationshipType.CALLS) == 2
    assert rel_type.count(RelationshipType.IMPORTS) == 1
    assert rel_type.count(RelationshipType.USES) == 1


def test_self_loop_index(relationship_graph_view):
    builder = IndexBuilder()
    loop_idx = builder.build_self_loop_index(relationship_graph_view)

    assert loop_idx.contains("n3") is True
    assert loop_idx.contains("n1") is False
    assert loop_idx.count() == 1


def test_dangling_edge_rejection():
    builder = GraphViewBuilder()
    identity = GraphIdentity(repository_id=RepositoryId("r1"), snapshot_id=SnapshotId("s1"))
    builder.set_metadata(GraphMetadata(identity=identity))
    builder.set_snapshot(GraphSnapshotInfo(snapshot_id=SnapshotId("s1")))

    n1 = ImmutableNodeView(node_id=NodeId("n1"), name="n1", qualified_name="n1", node_type="FN")
    e1 = ImmutableEdgeView(edge_id=EdgeId("e1"), source_node_id=NodeId("n1"), target_node_id=NodeId("n_missing"), relationship_type=RelationshipType.CALLS)
    builder.add_node(n1).add_edge(e1)

    # Build unvalidated graph view to simulate dangling edge
    unvalidated_view = builder.build()
    idx_builder = IndexBuilder()

    with pytest.raises(DanglingEdgeError):
        idx_builder.build_csr_adjacency_index(unvalidated_view)


def test_registry_relationship_indexes(relationship_graph_view):
    registry = IndexRegistry()
    assert registry.contains("CSRAdjacencyIndex") is True
    assert registry.contains("ReverseCSRAdjacencyIndex") is True

    csr = IndexFactory.create_index("CSRAdjacencyIndex", relationship_graph_view)
    assert csr.index_name == "CSRAdjacencyIndex"


def test_thread_safe_parallel_csr_lookups(relationship_graph_view):
    builder = IndexBuilder()
    csr = builder.build_csr_adjacency_index(relationship_graph_view)

    def worker_lookup(node_id_str: str):
        return csr.neighbors(node_id_str)

    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = [executor.submit(worker_lookup, "n1") for _ in range(100)]
        results = [f.result() for f in futures]

    assert all(set(r) == {"n2", "n3"} for r in results)
