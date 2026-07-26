"""
Comprehensive unit test suite for Core Lookup Indexes (NodeIndex, EdgeIndex, SymbolIndex, FileIndex, PackageIndex, NamespaceIndex, QualifiedNameIndex).
"""

from concurrent.futures import ThreadPoolExecutor
import pytest
from pydantic import ValidationError as PydanticValidationError

from graph_query_engine.errors import (
    DuplicateQualifiedNameError,
    IndexLookupError,
)
from graph_query_engine.index import (
    EdgeIndex,
    FileIndex,
    IndexBuilder,
    IndexFactory,
    IndexRegistry,
    NamespaceIndex,
    NodeIndex,
    PackageIndex,
    QualifiedNameIndex,
    SymbolIndex,
)
from graph_query_engine.types import (
    EdgeId,
    FileId,
    NamespaceId,
    NodeId,
    PackageId,
    RelationshipType,
    RepositoryId,
    SnapshotId,
    SymbolId,
)
from graph_query_engine.view.builder import GraphViewBuilder
from graph_query_engine.view.edge_view import ImmutableEdgeView
from graph_query_engine.view.identity import GraphIdentity
from graph_query_engine.view.metadata import GraphMetadata
from graph_query_engine.view.node_view import ImmutableNodeView
from graph_query_engine.view.snapshot import GraphSnapshotInfo


@pytest.fixture
def sample_graph_view():
    builder = GraphViewBuilder()
    identity = GraphIdentity(repository_id=RepositoryId("repo_test"), snapshot_id=SnapshotId("snap_test"))
    builder.set_metadata(GraphMetadata(identity=identity))
    builder.set_snapshot(GraphSnapshotInfo(snapshot_id=SnapshotId("snap_test")))

    n1 = ImmutableNodeView(
        node_id=NodeId("n1"),
        name="fn_auth",
        qualified_name="auth.service.fn_auth",
        node_type="FUNCTION",
        file=FileId("src/auth.py"),
        package=PackageId("auth_pkg"),
        namespace=NamespaceId("auth_ns"),
    )
    n2 = ImmutableNodeView(
        node_id=NodeId("n2"),
        name="fn_db",
        qualified_name="db.service.fn_db",
        node_type="FUNCTION",
        file=FileId("src/db.py"),
        package=PackageId("db_pkg"),
        namespace=NamespaceId("db_ns"),
    )
    n3 = ImmutableNodeView(
        node_id=NodeId("n3"),
        name="fn_util",
        qualified_name="auth.service.fn_util",
        node_type="FUNCTION",
        file=FileId("src/auth.py"),
        package=PackageId("auth_pkg"),
        namespace=NamespaceId("auth_ns"),
    )

    e1 = ImmutableEdgeView(
        edge_id=EdgeId("e1"),
        source_node_id=NodeId("n1"),
        target_node_id=NodeId("n2"),
        relationship_type=RelationshipType.CALLS,
    )

    builder.add_nodes([n1, n2, n3]).add_edge(e1)
    return builder.build()


def test_node_index_lookups(sample_graph_view):
    builder = IndexBuilder()
    idx = builder.build_node_index(sample_graph_view)

    assert idx.contains("n1") is True
    assert idx.exists("n2") is True
    assert idx.contains("n999") is False

    n1 = idx.get("n1")
    assert n1.name == "fn_auth"

    assert idx.try_get("n999") is None

    with pytest.raises(IndexLookupError):
        idx.get("n999")

    assert idx.size() == 3
    assert set(idx.keys()) == {"n1", "n2", "n3"}


def test_edge_index_lookups(sample_graph_view):
    builder = IndexBuilder()
    idx = builder.build_edge_index(sample_graph_view)

    assert idx.contains("e1") is True
    assert idx.size() == 1

    e1 = idx.get("e1")
    assert e1.relationship_type == RelationshipType.CALLS

    with pytest.raises(IndexLookupError):
        idx.get("e999")


def test_symbol_index_lookups(sample_graph_view):
    builder = IndexBuilder()
    idx = builder.build_symbol_index(sample_graph_view)

    assert idx.contains("n1") is True
    assert idx.count() == 3

    sym1 = idx.get("n1")
    assert sym1.qualified_name == "auth.service.fn_auth"


def test_file_index_grouping(sample_graph_view):
    builder = IndexBuilder()
    idx = builder.build_file_index(sample_graph_view)

    assert idx.contains("src/auth.py") is True
    auth_nodes = idx.get("src/auth.py")
    assert len(auth_nodes) == 2

    assert idx.count() == 2


def test_package_index_grouping(sample_graph_view):
    builder = IndexBuilder()
    idx = builder.build_package_index(sample_graph_view)

    assert idx.contains("auth_pkg") is True
    pkg_nodes = idx.get("auth_pkg")
    assert len(pkg_nodes) == 2


def test_namespace_index_grouping(sample_graph_view):
    builder = IndexBuilder()
    idx = builder.build_namespace_index(sample_graph_view)

    assert idx.contains("auth_ns") is True
    ns_nodes = idx.get("auth_ns")
    assert len(ns_nodes) == 2


def test_qualified_name_index(sample_graph_view):
    builder = IndexBuilder()
    idx = builder.build_qualified_name_index(sample_graph_view)

    assert idx.contains("auth.service.fn_auth") is True
    node = idx.get("auth.service.fn_auth")
    assert node.node_id == "n1"


def test_duplicate_qualified_name_rejection():
    builder = GraphViewBuilder()
    identity = GraphIdentity(repository_id=RepositoryId("r1"), snapshot_id=SnapshotId("s1"))
    builder.set_metadata(GraphMetadata(identity=identity))
    builder.set_snapshot(GraphSnapshotInfo(snapshot_id=SnapshotId("s1")))

    n1 = ImmutableNodeView(node_id=NodeId("n1"), name="a", qualified_name="dup.name", node_type="FN")
    n2 = ImmutableNodeView(node_id=NodeId("n2"), name="b", qualified_name="dup.name", node_type="FN")
    builder.add_nodes([n1, n2])

    graph_view = builder.build()
    idx_builder = IndexBuilder()

    with pytest.raises(DuplicateQualifiedNameError):
        idx_builder.build_qualified_name_index(graph_view, allow_duplicates=False)


def test_registry_pre_registered_indexes(sample_graph_view):
    registry = IndexRegistry()
    assert registry.contains("NodeIndex") is True
    assert registry.contains("EdgeIndex") is True
    assert registry.contains("SymbolIndex") is True

    # Factory manufacturing via registry types
    node_idx = IndexFactory.create_index("NodeIndex", sample_graph_view)
    edge_idx = IndexFactory.create_index("EdgeIndex", sample_graph_view)

    assert node_idx.index_name == "NodeIndex"
    assert edge_idx.index_name == "EdgeIndex"


def test_thread_safe_parallel_read_lookups(sample_graph_view):
    builder = IndexBuilder()
    idx = builder.build_node_index(sample_graph_view)

    def worker_lookup(node_id_str: str) -> bool:
        return idx.contains(node_id_str)

    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = [executor.submit(worker_lookup, "n1") for _ in range(100)]
        results = [f.result() for f in futures]

    assert all(results)
