"""
Comprehensive unit test suite for Semantic Indexes (TypeHierarchyIndex, InheritanceIndex, InterfaceImplementationIndex, APIRouteIndex, SymbolReferenceIndex, ImportIndex, ModuleIndex, LanguageIndex, AnnotationIndex, AttributeIndex, SemanticIndexRegistry).
"""

from concurrent.futures import ThreadPoolExecutor
import pytest

from graph_query_engine.errors import DuplicateRouteError, IndexLookupError
from graph_query_engine.index import (
    AnnotationIndex,
    APIRouteIndex,
    AttributeIndex,
    ImportIndex,
    IndexBuilder,
    IndexFactory,
    InheritanceIndex,
    InterfaceImplementationIndex,
    LanguageIndex,
    ModuleIndex,
    SemanticIndexRegistry,
    SymbolReferenceIndex,
    TypeHierarchyIndex,
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
def semantic_graph_view():
    builder = GraphViewBuilder()
    identity = GraphIdentity(repository_id=RepositoryId("repo_sem"), snapshot_id=SnapshotId("snap_sem"))
    builder.set_metadata(GraphMetadata(identity=identity))
    builder.set_snapshot(GraphSnapshotInfo(snapshot_id=SnapshotId("snap_sem")))

    # Base Class Node
    n_base = ImmutableNodeView(
        node_id=NodeId("n_base"),
        name="BaseService",
        qualified_name="app.services.BaseService",
        node_type="CLASS",
        language=LanguageId("python"),
        file=FileId("app/services/base.py"),
        package=PackageId("services_pkg"),
        namespace=NamespaceId("services"),
        attributes={"visibility": "public"},
    )
    # Derived Class Node
    n_derived = ImmutableNodeView(
        node_id=NodeId("n_derived"),
        name="AuthService",
        qualified_name="app.services.AuthService",
        node_type="CLASS",
        language=LanguageId("python"),
        file=FileId("app/services/auth.py"),
        package=PackageId("services_pkg"),
        namespace=NamespaceId("services"),
        attributes={"visibility": "public"},
    )
    # Interface Node
    n_iface = ImmutableNodeView(
        node_id=NodeId("n_iface"),
        name="IAuthService",
        qualified_name="app.interfaces.IAuthService",
        node_type="INTERFACE",
        language=LanguageId("python"),
        file=FileId("app/interfaces/auth.py"),
        package=PackageId("interfaces_pkg"),
        namespace=NamespaceId("interfaces"),
    )
    # API Route Handler Node
    n_handler = ImmutableNodeView(
        node_id=NodeId("n_handler"),
        name="login_handler",
        qualified_name="app.api.login_handler",
        node_type="FUNCTION",
        language=LanguageId("python"),
        file=FileId("app/api/auth_routes.py"),
        package=PackageId("api_pkg"),
        namespace=NamespaceId("api"),
        attributes={
            "http_method": "POST",
            "route_path": "/api/v1/login",
            "controller": "AuthController",
            "decorators": ["@app.post", "@dataclass"],
            "visibility": "public",
            "is_async": "true",
        },
    )

    # Relationships
    e_inherits = ImmutableEdgeView(
        edge_id=EdgeId("e_inh"),
        source_node_id=NodeId("n_derived"),
        target_node_id=NodeId("n_base"),
        relationship_type=RelationshipType.INHERITS,
    )
    e_implements = ImmutableEdgeView(
        edge_id=EdgeId("e_impl"),
        source_node_id=NodeId("n_derived"),
        target_node_id=NodeId("n_iface"),
        relationship_type=RelationshipType.IMPLEMENTS,
    )
    e_calls = ImmutableEdgeView(
        edge_id=EdgeId("e_calls"),
        source_node_id=NodeId("n_handler"),
        target_node_id=NodeId("n_derived"),
        relationship_type=RelationshipType.CALLS,
    )
    e_imports = ImmutableEdgeView(
        edge_id=EdgeId("e_imp"),
        source_node_id=NodeId("n_handler"),
        target_node_id=NodeId("n_derived"),
        relationship_type=RelationshipType.IMPORTS,
    )

    builder.add_nodes([n_base, n_derived, n_iface, n_handler])
    builder.add_edges([e_inherits, e_implements, e_calls, e_imports])
    return builder.build()


def test_type_hierarchy_index(semantic_graph_view):
    builder = IndexBuilder()
    idx = builder.build_type_hierarchy_index(semantic_graph_view)

    bases = idx.base_classes("n_derived")
    assert len(bases) == 1
    assert bases[0].node_id == "n_base"

    children = idx.derived_classes("n_base")
    assert len(children) == 1
    assert children[0].node_id == "n_derived"


def test_inheritance_index(semantic_graph_view):
    builder = IndexBuilder()
    idx = builder.build_inheritance_index(semantic_graph_view)

    ifaces = idx.interfaces()
    assert len(ifaces) == 1
    assert ifaces[0].node_id == "n_iface"


def test_interface_implementation_index(semantic_graph_view):
    builder = IndexBuilder()
    idx = builder.build_interface_implementation_index(semantic_graph_view)

    impls = idx.implementations("n_iface")
    assert len(impls) == 1
    assert impls[0].node_id == "n_derived"

    ifaces = idx.interfaces_for("n_derived")
    assert len(ifaces) == 1
    assert ifaces[0].node_id == "n_iface"


def test_api_route_index(semantic_graph_view):
    builder = IndexBuilder()
    idx = builder.build_api_route_index(semantic_graph_view)

    assert idx.contains("POST", "/api/v1/login") is True
    route = idx.get("POST", "/api/v1/login")
    assert route.handler_node.node_id == "n_handler"
    assert route.controller_name == "AuthController"


def test_duplicate_api_route_rejection():
    builder = GraphViewBuilder()
    identity = GraphIdentity(repository_id=RepositoryId("r1"), snapshot_id=SnapshotId("s1"))
    builder.set_metadata(GraphMetadata(identity=identity))
    builder.set_snapshot(GraphSnapshotInfo(snapshot_id=SnapshotId("s1")))

    n1 = ImmutableNodeView(node_id=NodeId("n1"), name="h1", qualified_name="h1", node_type="FN", attributes={"http_method": "GET", "route_path": "/dup"})
    n2 = ImmutableNodeView(node_id=NodeId("n2"), name="h2", qualified_name="h2", node_type="FN", attributes={"http_method": "GET", "route_path": "/dup"})
    builder.add_nodes([n1, n2])

    graph_view = builder.build()
    idx_builder = IndexBuilder()

    with pytest.raises(DuplicateRouteError):
        idx_builder.build_api_route_index(graph_view, allow_duplicate_routes=False)


def test_symbol_reference_index(semantic_graph_view):
    builder = IndexBuilder()
    idx = builder.build_symbol_reference_index(semantic_graph_view)

    refs = idx.references("n_derived")
    assert len(refs) == 1
    assert refs[0].node_id == "n_handler"


def test_import_index(semantic_graph_view):
    builder = IndexBuilder()
    idx = builder.build_import_index(semantic_graph_view)

    imported = idx.imports_by_file("app/api/auth_routes.py")
    assert len(imported) == 1
    assert imported[0].node_id == "n_derived"


def test_module_index(semantic_graph_view):
    builder = IndexBuilder()
    idx = builder.build_module_index(semantic_graph_view)

    assert "services" in idx.modules()
    services_symbols = idx.symbols_in_module("services")
    assert len(services_symbols) == 2


def test_language_index(semantic_graph_view):
    builder = IndexBuilder()
    idx = builder.build_language_index(semantic_graph_view)

    py_symbols = idx.symbols_by_language("python")
    assert len(py_symbols) == 4


def test_annotation_index(semantic_graph_view):
    builder = IndexBuilder()
    idx = builder.build_annotation_index(semantic_graph_view)

    nodes = idx.by_annotation("@app.post")
    assert len(nodes) == 1
    assert nodes[0].node_id == "n_handler"


def test_attribute_index(semantic_graph_view):
    builder = IndexBuilder()
    idx = builder.build_attribute_index(semantic_graph_view)

    public_nodes = idx.public_symbols()
    assert len(public_nodes) == 4

    async_nodes = idx.async_symbols()
    assert len(async_nodes) == 1
    assert async_nodes[0].node_id == "n_handler"


def test_semantic_index_registry(semantic_graph_view):
    reg = SemanticIndexRegistry()
    assert reg.contains("TypeHierarchyIndex") is True
    assert reg.contains("APIRouteIndex") is True

    idx = IndexFactory.create_index("APIRouteIndex", semantic_graph_view)
    reg.register_instance(idx)

    assert reg.has_index("APIRouteIndex") is True
    assert reg.get_index("APIRouteIndex") is not None


def test_thread_safe_parallel_semantic_lookups(semantic_graph_view):
    builder = IndexBuilder()
    idx = builder.build_api_route_index(semantic_graph_view)

    def worker_lookup():
        return idx.get("POST", "/api/v1/login")

    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = [executor.submit(worker_lookup) for _ in range(100)]
        results = [f.result() for f in futures]

    assert all(r.handler_node.node_id == "n_handler" for r in results)
