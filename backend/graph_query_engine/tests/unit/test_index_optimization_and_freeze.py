"""
Comprehensive unit test suite for Step 3.5 (Index Validation Engine, Consistency Checker, Integrity Checker, Freeze Validator, Diagnostics, Reports, Manifest, Snapshot, Benchmarks).
"""

from concurrent.futures import ThreadPoolExecutor
import pytest

from graph_query_engine.index import (
    DiagnosticSeverity,
    HealthStatus,
    IndexBenchmarkSuite,
    IndexBuilder,
    IndexConsistencyChecker,
    IndexDiagnostics,
    IndexFactory,
    IndexFreezeValidator,
    IndexHealthReport,
    IndexIntegrityChecker,
    IndexManifest,
    IndexMemoryReport,
    IndexMetrics,
    IndexPerformanceReport,
    IndexRegistry,
    IndexSnapshot,
    IndexStatisticsCollector,
    IndexValidationEngine,
)
from graph_query_engine.types import (
    EdgeId,
    FileId,
    LanguageId,
    NamespaceId,
    NodeId,
    PackageId,
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


@pytest.fixture
def sample_graph_view():
    builder = GraphViewBuilder()
    identity = GraphIdentity(repository_id=RepositoryId("repo_h"), snapshot_id=SnapshotId("snap_h"))
    builder.set_metadata(GraphMetadata(identity=identity))
    builder.set_snapshot(GraphSnapshotInfo(snapshot_id=SnapshotId("snap_h")))

    n1 = ImmutableNodeView(
        node_id=NodeId("n1"),
        name="Node1",
        qualified_name="pkg.Node1",
        node_type="CLASS",
        attributes={"visibility": "public"},
    )
    n2 = ImmutableNodeView(
        node_id=NodeId("n2"),
        name="Node2",
        qualified_name="pkg.Node2",
        node_type="CLASS",
        attributes={"visibility": "public"},
    )
    e1 = ImmutableEdgeView(
        edge_id=EdgeId("e1"),
        source_node_id=NodeId("n1"),
        target_node_id=NodeId("n2"),
        relationship_type=RelationshipType.CALLS,
    )

    builder.add_nodes([n1, n2])
    builder.add_edges([e1])
    return builder.build()


def test_index_integrity_checker(sample_graph_view):
    builder = IndexBuilder()
    node_idx = builder.build_node_index(sample_graph_view)

    diag = IndexIntegrityChecker.check(node_idx)
    assert diag.has_errors is False
    assert len(diag.items) == 0


def test_index_consistency_checker(sample_graph_view):
    builder = IndexBuilder()
    node_idx = builder.build_node_index(sample_graph_view)
    edge_idx = builder.build_edge_index(sample_graph_view)

    diag = IndexConsistencyChecker.verify_consistency(node_idx, edge_idx)
    assert diag.has_errors is False


def test_index_consistency_checker_dangling_reference(sample_graph_view):
    builder = IndexBuilder()
    node_idx = builder.build_node_index(sample_graph_view)

    # Edge referencing non-existent n99
    bad_edge = ImmutableEdgeView(
        edge_id=EdgeId("e_bad"),
        source_node_id=NodeId("n1"),
        target_node_id=NodeId("n99"),
        relationship_type=RelationshipType.CALLS,
    )
    b = GraphViewBuilder()
    identity = GraphIdentity(repository_id=RepositoryId("r"), snapshot_id=SnapshotId("s"))
    b.set_metadata(GraphMetadata(identity=identity))
    b.set_snapshot(GraphSnapshotInfo(snapshot_id=SnapshotId("s")))
    b.add_nodes([sample_graph_view.nodes["n1"]])
    b.add_edges([bad_edge])
    bad_view = b.build()

    edge_idx = builder.build_edge_index(bad_view)

    diag = IndexConsistencyChecker.verify_consistency(node_idx, edge_idx)
    assert diag.has_errors is True
    assert any("n99" in item.message for item in diag.items)


def test_index_validation_engine(sample_graph_view):
    reg = IndexRegistry()
    node_idx = IndexFactory.create_index("NodeIndex", sample_graph_view)
    edge_idx = IndexFactory.create_index("EdgeIndex", sample_graph_view)
    reg.register_instance(node_idx)
    reg.register_instance(edge_idx)

    report = IndexValidationEngine.validate_registry(reg)
    assert report.status == HealthStatus.HEALTHY
    assert len(report.errors) == 0


def test_index_snapshot_and_manifest(sample_graph_view):
    identity = sample_graph_view.metadata.identity
    snap = IndexSnapshot(
        snapshot_id="snap_idx_001",
        graph_identity=identity,
        active_index_names=("NodeIndex", "EdgeIndex"),
    )
    assert snap.snapshot_id == "snap_idx_001"
    assert "NodeIndex" in snap.active_index_names

    manifest = IndexManifest(
        registered_index_types=("NodeIndex", "EdgeIndex", "CSRAdjacencyIndex"),
    )
    assert len(manifest.registered_index_types) == 3


def test_index_benchmark_suite(sample_graph_view):
    report = IndexBenchmarkSuite.run_benchmarks(sample_graph_view)
    assert isinstance(report, IndexPerformanceReport)
    assert report.total_indexes == 5
    assert report.estimated_total_memory_bytes > 0


def test_index_memory_report():
    mem_rep = IndexMemoryReport(
        lookup_index_bytes=1024,
        relationship_index_bytes=2048,
        semantic_index_bytes=4096,
        total_memory_bytes=7168,
        object_counts=10,
    )
    assert mem_rep.total_memory_bytes == 7168


def test_index_metrics():
    metrics = IndexStatisticsCollector.collect(registered_count=25, build_count=5, validation_count=10)
    assert metrics.registered_indexes_count == 25
    assert metrics.validation_count == 10


def test_index_freeze_validator():
    diag = IndexFreezeValidator.validate_readiness()
    assert diag.has_errors is False
    assert len(diag.items) == 0


def test_parallel_validation_and_benchmarks(sample_graph_view):
    def worker():
        return IndexBenchmarkSuite.run_benchmarks(sample_graph_view)

    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = [executor.submit(worker) for _ in range(50)]
        results = [f.result() for f in futures]

    assert all(r.total_indexes == 5 for r in results)
