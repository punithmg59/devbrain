"""
IndexBuilder for Assembling Immutable Core Lookup, Relationship, and Semantic Indexes from GraphView.
"""

import uuid
from typing import Iterable, Mapping, Optional, Self

from graph_query_engine.errors import (
    CSRConstructionError,
    DanglingEdgeError,
    DuplicateEdgeError,
    DuplicateNodeError,
    DuplicateQualifiedNameError,
    DuplicateRouteError,
    DuplicateSymbolError,
    ValidationError,
)
from graph_query_engine.index.annotation_index import AnnotationIndex
from graph_query_engine.index.api_route_index import APIRouteIndex, APIRouteRecord
from graph_query_engine.index.attribute_index import AttributeIndex
from graph_query_engine.index.base import BaseIndex
from graph_query_engine.index.csr_adjacency_index import CSRAdjacencyIndex
from graph_query_engine.index.descriptor import IndexDescriptor
from graph_query_engine.index.edge_index import EdgeIndex
from graph_query_engine.index.file_index import FileIndex
from graph_query_engine.index.import_index import ImportIndex
from graph_query_engine.index.incoming_relationship_index import IncomingRelationshipIndex
from graph_query_engine.index.inheritance_index import InheritanceIndex
from graph_query_engine.index.interface_implementation_index import InterfaceImplementationIndex
from graph_query_engine.index.language_index import LanguageIndex
from graph_query_engine.index.metadata import IndexMetadata
from graph_query_engine.index.module_index import ModuleIndex
from graph_query_engine.index.namespace_index import NamespaceIndex
from graph_query_engine.index.node_index import NodeIndex
from graph_query_engine.index.node_relationship_index import NodeRelationshipIndex
from graph_query_engine.index.outgoing_relationship_index import OutgoingRelationshipIndex
from graph_query_engine.index.package_index import PackageIndex
from graph_query_engine.index.qualified_name_index import QualifiedNameIndex
from graph_query_engine.index.relationship_index import RelationshipIndex
from graph_query_engine.index.relationship_type_index import RelationshipTypeIndex
from graph_query_engine.index.reverse_csr_adjacency_index import ReverseCSRAdjacencyIndex
from graph_query_engine.index.self_loop_index import SelfLoopIndex
from graph_query_engine.index.statistics import IndexStatistics
from graph_query_engine.index.symbol_index import SymbolIndex
from graph_query_engine.index.symbol_reference_index import SymbolReferenceIndex
from graph_query_engine.index.type_hierarchy_index import TypeHierarchyIndex
from graph_query_engine.index.validation import IndexValidator
from graph_query_engine.types import (
    EdgeId,
    FileId,
    LanguageId,
    NamespaceId,
    NodeId,
    PackageId,
    RelationshipType,
    SymbolId,
)
from graph_query_engine.view.edge_view import ImmutableEdgeView
from graph_query_engine.view.graph_view import GraphView
from graph_query_engine.view.node_view import ImmutableNodeView


class IndexBuilder:
    """
    Builder assembling IndexDescriptor, IndexMetadata, Statistics, and concrete lookup, relationship, and semantic indexes from GraphView.
    """

    def __init__(self) -> None:
        self._descriptor: Optional[IndexDescriptor] = None
        self._metadata: Optional[IndexMetadata] = None
        self._statistics: Optional[IndexStatistics] = None

    def set_descriptor(self, descriptor: IndexDescriptor) -> Self:
        """Sets the index descriptor."""
        self._descriptor = descriptor
        return self

    def set_metadata(self, metadata: IndexMetadata) -> Self:
        """Sets index metadata."""
        self._metadata = metadata
        return self

    def set_statistics(self, statistics: IndexStatistics) -> Self:
        """Sets index statistics."""
        self._statistics = statistics
        return self

    # --- Step 3.2 Core Lookup Indexes ---
    def build_node_index(self, graph_view: GraphView) -> NodeIndex:
        desc = self._descriptor or IndexDescriptor(name="NodeIndex", index_type="LOOKUP")
        meta = self._metadata or IndexMetadata(source_graph_version=graph_view.metadata.graph_version)
        stats = self._statistics or IndexStatistics(node_count=len(graph_view.nodes), edge_count=len(graph_view.edges))

        idx = NodeIndex(
            index_id=f"idx_node_{uuid.uuid4().hex[:8]}",
            descriptor=desc,
            metadata=meta,
            statistics=stats,
            graph_identity=graph_view.metadata.identity,
            node_map=dict(graph_view.nodes),
        )
        self._validate_or_raise(idx)
        return idx

    def build_edge_index(self, graph_view: GraphView) -> EdgeIndex:
        desc = self._descriptor or IndexDescriptor(name="EdgeIndex", index_type="LOOKUP")
        meta = self._metadata or IndexMetadata(source_graph_version=graph_view.metadata.graph_version)
        stats = self._statistics or IndexStatistics(node_count=len(graph_view.nodes), edge_count=len(graph_view.edges))

        idx = EdgeIndex(
            index_id=f"idx_edge_{uuid.uuid4().hex[:8]}",
            descriptor=desc,
            metadata=meta,
            statistics=stats,
            graph_identity=graph_view.metadata.identity,
            edge_map=dict(graph_view.edges),
        )
        self._validate_or_raise(idx)
        return idx

    def build_symbol_index(self, graph_view: GraphView) -> SymbolIndex:
        desc = self._descriptor or IndexDescriptor(name="SymbolIndex", index_type="LOOKUP")
        meta = self._metadata or IndexMetadata(source_graph_version=graph_view.metadata.graph_version)
        stats = self._statistics or IndexStatistics(node_count=len(graph_view.nodes))

        symbol_map: dict[SymbolId, ImmutableNodeView] = {}
        for nid, node in graph_view.nodes.items():
            sid = SymbolId(str(nid))
            if sid in symbol_map:
                raise DuplicateSymbolError(f"Duplicate SymbolId '{sid}' found during symbol index build.")
            symbol_map[sid] = node

        idx = SymbolIndex(
            index_id=f"idx_sym_{uuid.uuid4().hex[:8]}",
            descriptor=desc,
            metadata=meta,
            statistics=stats,
            graph_identity=graph_view.metadata.identity,
            symbol_map=symbol_map,
        )
        self._validate_or_raise(idx)
        return idx

    def build_file_index(self, graph_view: GraphView) -> FileIndex:
        desc = self._descriptor or IndexDescriptor(name="FileIndex", index_type="GROUPING")
        meta = self._metadata or IndexMetadata(source_graph_version=graph_view.metadata.graph_version)
        stats = self._statistics or IndexStatistics(node_count=len(graph_view.nodes))

        file_groups: dict[FileId, list[ImmutableNodeView]] = {}
        for node in graph_view.nodes.values():
            fid = FileId(str(node.file)) if node.file else FileId("unassigned")
            if fid not in file_groups:
                file_groups[fid] = []
            file_groups[fid].append(node)

        idx = FileIndex(
            index_id=f"idx_file_{uuid.uuid4().hex[:8]}",
            descriptor=desc,
            metadata=meta,
            statistics=stats,
            graph_identity=graph_view.metadata.identity,
            file_map={k: tuple(v) for k, v in file_groups.items()},
        )
        self._validate_or_raise(idx)
        return idx

    def build_package_index(self, graph_view: GraphView) -> PackageIndex:
        desc = self._descriptor or IndexDescriptor(name="PackageIndex", index_type="GROUPING")
        meta = self._metadata or IndexMetadata(source_graph_version=graph_view.metadata.graph_version)
        stats = self._statistics or IndexStatistics(node_count=len(graph_view.nodes))

        pkg_groups: dict[PackageId, list[ImmutableNodeView]] = {}
        for node in graph_view.nodes.values():
            pid = PackageId(str(node.package)) if node.package else PackageId("default_package")
            if pid not in pkg_groups:
                pkg_groups[pid] = []
            pkg_groups[pid].append(node)

        idx = PackageIndex(
            index_id=f"idx_pkg_{uuid.uuid4().hex[:8]}",
            descriptor=desc,
            metadata=meta,
            statistics=stats,
            graph_identity=graph_view.metadata.identity,
            package_map={k: tuple(v) for k, v in pkg_groups.items()},
        )
        self._validate_or_raise(idx)
        return idx

    def build_namespace_index(self, graph_view: GraphView) -> NamespaceIndex:
        desc = self._descriptor or IndexDescriptor(name="NamespaceIndex", index_type="GROUPING")
        meta = self._metadata or IndexMetadata(source_graph_version=graph_view.metadata.graph_version)
        stats = self._statistics or IndexStatistics(node_count=len(graph_view.nodes))

        ns_groups: dict[NamespaceId, list[ImmutableNodeView]] = {}
        for node in graph_view.nodes.values():
            nsid = NamespaceId(str(node.namespace)) if node.namespace else NamespaceId("global_namespace")
            if nsid not in ns_groups:
                ns_groups[nsid] = []
            ns_groups[nsid].append(node)

        idx = NamespaceIndex(
            index_id=f"idx_ns_{uuid.uuid4().hex[:8]}",
            descriptor=desc,
            metadata=meta,
            statistics=stats,
            graph_identity=graph_view.metadata.identity,
            namespace_map={k: tuple(v) for k, v in ns_groups.items()},
        )
        self._validate_or_raise(idx)
        return idx

    def build_qualified_name_index(self, graph_view: GraphView, allow_duplicates: bool = False) -> QualifiedNameIndex:
        desc = self._descriptor or IndexDescriptor(name="QualifiedNameIndex", index_type="LOOKUP")
        meta = self._metadata or IndexMetadata(source_graph_version=graph_view.metadata.graph_version)
        stats = self._statistics or IndexStatistics(node_count=len(graph_view.nodes))

        name_map: dict[str, ImmutableNodeView] = {}
        for node in graph_view.nodes.values():
            qname = node.qualified_name
            if not qname:
                continue
            if qname in name_map and not allow_duplicates:
                raise DuplicateQualifiedNameError(f"Duplicate qualified name '{qname}' encountered during index build.")
            name_map[qname] = node

        idx = QualifiedNameIndex(
            index_id=f"idx_qname_{uuid.uuid4().hex[:8]}",
            descriptor=desc,
            metadata=meta,
            statistics=stats,
            graph_identity=graph_view.metadata.identity,
            name_map=name_map,
        )
        self._validate_or_raise(idx)
        return idx

    # --- Step 3.3 Relationship Indexes ---
    def build_csr_adjacency_index(self, graph_view: GraphView) -> CSRAdjacencyIndex:
        desc = self._descriptor or IndexDescriptor(name="CSRAdjacencyIndex", index_type="ADJACENCY")
        meta = self._metadata or IndexMetadata(source_graph_version=graph_view.metadata.graph_version)
        stats = self._statistics or IndexStatistics(node_count=len(graph_view.nodes), edge_count=len(graph_view.edges))

        sorted_node_ids = sorted(graph_view.nodes.keys())
        node_id_map = {nid: idx for idx, nid in enumerate(sorted_node_ids)}

        offsets = [0]
        target_nodes: list[NodeId] = []
        edge_ids: list[EdgeId] = []

        for nid in sorted_node_ids:
            outgoing = [e for e in graph_view.edges.values() if e.source_node_id == nid]
            for e in outgoing:
                if e.target_node_id not in graph_view.nodes:
                    raise DanglingEdgeError(f"Edge '{e.edge_id}' references non-existent target node '{e.target_node_id}'.")
                target_nodes.append(e.target_node_id)
                edge_ids.append(e.edge_id)
            offsets.append(len(target_nodes))

        idx = CSRAdjacencyIndex(
            index_id=f"idx_csr_{uuid.uuid4().hex[:8]}",
            descriptor=desc,
            metadata=meta,
            statistics=stats,
            graph_identity=graph_view.metadata.identity,
            node_offsets=tuple(offsets),
            node_id_map=node_id_map,
            target_nodes=tuple(target_nodes),
            edge_ids=tuple(edge_ids),
        )
        self._validate_or_raise(idx)
        return idx

    def build_reverse_csr_adjacency_index(self, graph_view: GraphView) -> ReverseCSRAdjacencyIndex:
        desc = self._descriptor or IndexDescriptor(name="ReverseCSRAdjacencyIndex", index_type="ADJACENCY")
        meta = self._metadata or IndexMetadata(source_graph_version=graph_view.metadata.graph_version)
        stats = self._statistics or IndexStatistics(node_count=len(graph_view.nodes), edge_count=len(graph_view.edges))

        sorted_node_ids = sorted(graph_view.nodes.keys())
        node_id_map = {nid: idx for idx, nid in enumerate(sorted_node_ids)}

        offsets = [0]
        source_nodes: list[NodeId] = []
        edge_ids: list[EdgeId] = []

        for nid in sorted_node_ids:
            incoming = [e for e in graph_view.edges.values() if e.target_node_id == nid]
            for e in incoming:
                if e.source_node_id not in graph_view.nodes:
                    raise DanglingEdgeError(f"Edge '{e.edge_id}' references non-existent source node '{e.source_node_id}'.")
                source_nodes.append(e.source_node_id)
                edge_ids.append(e.edge_id)
            offsets.append(len(source_nodes))

        idx = ReverseCSRAdjacencyIndex(
            index_id=f"idx_rcsr_{uuid.uuid4().hex[:8]}",
            descriptor=desc,
            metadata=meta,
            statistics=stats,
            graph_identity=graph_view.metadata.identity,
            node_offsets=tuple(offsets),
            node_id_map=node_id_map,
            source_nodes=tuple(source_nodes),
            edge_ids=tuple(edge_ids),
        )
        self._validate_or_raise(idx)
        return idx

    def build_relationship_index(self, graph_view: GraphView) -> RelationshipIndex:
        desc = self._descriptor or IndexDescriptor(name="RelationshipIndex", index_type="RELATIONSHIP")
        meta = self._metadata or IndexMetadata(source_graph_version=graph_view.metadata.graph_version)
        stats = self._statistics or IndexStatistics(edge_count=len(graph_view.edges))

        idx = RelationshipIndex(
            index_id=f"idx_rel_{uuid.uuid4().hex[:8]}",
            descriptor=desc,
            metadata=meta,
            statistics=stats,
            graph_identity=graph_view.metadata.identity,
            edge_map=dict(graph_view.edges),
        )
        self._validate_or_raise(idx)
        return idx

    def build_outgoing_relationship_index(self, graph_view: GraphView) -> OutgoingRelationshipIndex:
        desc = self._descriptor or IndexDescriptor(name="OutgoingRelationshipIndex", index_type="RELATIONSHIP")
        meta = self._metadata or IndexMetadata(source_graph_version=graph_view.metadata.graph_version)
        stats = self._statistics or IndexStatistics(node_count=len(graph_view.nodes), edge_count=len(graph_view.edges))

        out_groups: dict[NodeId, list[ImmutableEdgeView]] = {nid: [] for nid in graph_view.nodes.keys()}
        for edge in graph_view.edges.values():
            if edge.source_node_id not in out_groups:
                out_groups[edge.source_node_id] = []
            out_groups[edge.source_node_id].append(edge)

        idx = OutgoingRelationshipIndex(
            index_id=f"idx_outrel_{uuid.uuid4().hex[:8]}",
            descriptor=desc,
            metadata=meta,
            statistics=stats,
            graph_identity=graph_view.metadata.identity,
            outgoing_map={k: tuple(v) for k, v in out_groups.items()},
        )
        self._validate_or_raise(idx)
        return idx

    def build_incoming_relationship_index(self, graph_view: GraphView) -> IncomingRelationshipIndex:
        desc = self._descriptor or IndexDescriptor(name="IncomingRelationshipIndex", index_type="RELATIONSHIP")
        meta = self._metadata or IndexMetadata(source_graph_version=graph_view.metadata.graph_version)
        stats = self._statistics or IndexStatistics(node_count=len(graph_view.nodes), edge_count=len(graph_view.edges))

        in_groups: dict[NodeId, list[ImmutableEdgeView]] = {nid: [] for nid in graph_view.nodes.keys()}
        for edge in graph_view.edges.values():
            if edge.target_node_id not in in_groups:
                in_groups[edge.target_node_id] = []
            in_groups[edge.target_node_id].append(edge)

        idx = IncomingRelationshipIndex(
            index_id=f"idx_inrel_{uuid.uuid4().hex[:8]}",
            descriptor=desc,
            metadata=meta,
            statistics=stats,
            graph_identity=graph_view.metadata.identity,
            incoming_map={k: tuple(v) for k, v in in_groups.items()},
        )
        self._validate_or_raise(idx)
        return idx

    def build_node_relationship_index(self, graph_view: GraphView) -> NodeRelationshipIndex:
        desc = self._descriptor or IndexDescriptor(name="NodeRelationshipIndex", index_type="RELATIONSHIP")
        meta = self._metadata or IndexMetadata(source_graph_version=graph_view.metadata.graph_version)
        stats = self._statistics or IndexStatistics(node_count=len(graph_view.nodes), edge_count=len(graph_view.edges))

        node_groups: dict[NodeId, list[ImmutableEdgeView]] = {nid: [] for nid in graph_view.nodes.keys()}
        for edge in graph_view.edges.values():
            if edge.source_node_id in node_groups:
                node_groups[edge.source_node_id].append(edge)
            if edge.target_node_id in node_groups and edge.target_node_id != edge.source_node_id:
                node_groups[edge.target_node_id].append(edge)

        idx = NodeRelationshipIndex(
            index_id=f"idx_noderel_{uuid.uuid4().hex[:8]}",
            descriptor=desc,
            metadata=meta,
            statistics=stats,
            graph_identity=graph_view.metadata.identity,
            relationship_map={k: tuple(v) for k, v in node_groups.items()},
        )
        self._validate_or_raise(idx)
        return idx

    def build_relationship_type_index(self, graph_view: GraphView) -> RelationshipTypeIndex:
        desc = self._descriptor or IndexDescriptor(name="RelationshipTypeIndex", index_type="RELATIONSHIP")
        meta = self._metadata or IndexMetadata(source_graph_version=graph_view.metadata.graph_version)
        stats = self._statistics or IndexStatistics(edge_count=len(graph_view.edges))

        type_groups: dict[str, list[ImmutableEdgeView]] = {}
        for edge in graph_view.edges.values():
            key = edge.relationship_type.name if hasattr(edge.relationship_type, "name") else str(edge.relationship_type)
            if key not in type_groups:
                type_groups[key] = []
            type_groups[key].append(edge)

        idx = RelationshipTypeIndex(
            index_id=f"idx_reltype_{uuid.uuid4().hex[:8]}",
            descriptor=desc,
            metadata=meta,
            statistics=stats,
            graph_identity=graph_view.metadata.identity,
            type_map={k: tuple(v) for k, v in type_groups.items()},
        )
        self._validate_or_raise(idx)
        return idx

    def build_self_loop_index(self, graph_view: GraphView) -> SelfLoopIndex:
        desc = self._descriptor or IndexDescriptor(name="SelfLoopIndex", index_type="RELATIONSHIP")
        meta = self._metadata or IndexMetadata(source_graph_version=graph_view.metadata.graph_version)
        stats = self._statistics or IndexStatistics(node_count=len(graph_view.nodes))

        loop_groups: dict[NodeId, list[ImmutableEdgeView]] = {}
        for edge in graph_view.edges.values():
            if edge.source_node_id == edge.target_node_id:
                nid = edge.source_node_id
                if nid not in loop_groups:
                    loop_groups[nid] = []
                loop_groups[nid].append(edge)

        idx = SelfLoopIndex(
            index_id=f"idx_loop_{uuid.uuid4().hex[:8]}",
            descriptor=desc,
            metadata=meta,
            statistics=stats,
            graph_identity=graph_view.metadata.identity,
            loop_map={k: tuple(v) for k, v in loop_groups.items()},
        )
        self._validate_or_raise(idx)
        return idx

    # --- Step 3.4 Semantic Indexes ---
    def build_type_hierarchy_index(self, graph_view: GraphView) -> TypeHierarchyIndex:
        desc = self._descriptor or IndexDescriptor(name="TypeHierarchyIndex", index_type="SEMANTIC")
        meta = self._metadata or IndexMetadata(source_graph_version=graph_view.metadata.graph_version)
        stats = self._statistics or IndexStatistics(node_count=len(graph_view.nodes))

        parent_map: dict[NodeId, list[ImmutableNodeView]] = {}
        child_map: dict[NodeId, list[ImmutableNodeView]] = {}

        for edge in graph_view.edges.values():
            if edge.relationship_type == RelationshipType.INHERITS:
                child_node = graph_view.nodes.get(edge.source_node_id)
                parent_node = graph_view.nodes.get(edge.target_node_id)
                if child_node and parent_node:
                    if child_node.node_id not in parent_map:
                        parent_map[child_node.node_id] = []
                    parent_map[child_node.node_id].append(parent_node)

                    if parent_node.node_id not in child_map:
                        child_map[parent_node.node_id] = []
                    child_map[parent_node.node_id].append(child_node)

        idx = TypeHierarchyIndex(
            index_id=f"idx_thier_{uuid.uuid4().hex[:8]}",
            descriptor=desc,
            metadata=meta,
            statistics=stats,
            graph_identity=graph_view.metadata.identity,
            parent_map={k: tuple(v) for k, v in parent_map.items()},
            child_map={k: tuple(v) for k, v in child_map.items()},
        )
        self._validate_or_raise(idx)
        return idx

    def build_inheritance_index(self, graph_view: GraphView) -> InheritanceIndex:
        desc = self._descriptor or IndexDescriptor(name="InheritanceIndex", index_type="SEMANTIC")
        meta = self._metadata or IndexMetadata(source_graph_version=graph_view.metadata.graph_version)
        stats = self._statistics or IndexStatistics(node_count=len(graph_view.nodes))

        kind_groups: dict[str, list[ImmutableNodeView]] = {
            "abstract": [],
            "interface": [],
            "trait": [],
            "mixin": [],
        }

        for node in graph_view.nodes.values():
            ntype = node.node_type.lower()
            if "interface" in ntype:
                kind_groups["interface"].append(node)
            elif "abstract" in ntype:
                kind_groups["abstract"].append(node)
            elif "trait" in ntype:
                kind_groups["trait"].append(node)
            elif "mixin" in ntype:
                kind_groups["mixin"].append(node)

        idx = InheritanceIndex(
            index_id=f"idx_inh_{uuid.uuid4().hex[:8]}",
            descriptor=desc,
            metadata=meta,
            statistics=stats,
            graph_identity=graph_view.metadata.identity,
            kind_map={k: tuple(v) for k, v in kind_groups.items()},
        )
        self._validate_or_raise(idx)
        return idx

    def build_interface_implementation_index(self, graph_view: GraphView) -> InterfaceImplementationIndex:
        desc = self._descriptor or IndexDescriptor(name="InterfaceImplementationIndex", index_type="SEMANTIC")
        meta = self._metadata or IndexMetadata(source_graph_version=graph_view.metadata.graph_version)
        stats = self._statistics or IndexStatistics(node_count=len(graph_view.nodes))

        iface_to_impls: dict[NodeId, list[ImmutableNodeView]] = {}
        cls_to_ifaces: dict[NodeId, list[ImmutableNodeView]] = {}

        for edge in graph_view.edges.values():
            if edge.relationship_type == RelationshipType.IMPLEMENTS:
                impl_node = graph_view.nodes.get(edge.source_node_id)
                iface_node = graph_view.nodes.get(edge.target_node_id)
                if impl_node and iface_node:
                    if iface_node.node_id not in iface_to_impls:
                        iface_to_impls[iface_node.node_id] = []
                    iface_to_impls[iface_node.node_id].append(impl_node)

                    if impl_node.node_id not in cls_to_ifaces:
                        cls_to_ifaces[impl_node.node_id] = []
                    cls_to_ifaces[impl_node.node_id].append(iface_node)

        idx = InterfaceImplementationIndex(
            index_id=f"idx_iface_{uuid.uuid4().hex[:8]}",
            descriptor=desc,
            metadata=meta,
            statistics=stats,
            graph_identity=graph_view.metadata.identity,
            interface_to_implementations={k: tuple(v) for k, v in iface_to_impls.items()},
            class_to_interfaces={k: tuple(v) for k, v in cls_to_ifaces.items()},
        )
        self._validate_or_raise(idx)
        return idx

    def build_api_route_index(self, graph_view: GraphView, allow_duplicate_routes: bool = False) -> APIRouteIndex:
        desc = self._descriptor or IndexDescriptor(name="APIRouteIndex", index_type="SEMANTIC")
        meta = self._metadata or IndexMetadata(source_graph_version=graph_view.metadata.graph_version)
        stats = self._statistics or IndexStatistics(node_count=len(graph_view.nodes))

        route_map: dict[str, APIRouteRecord] = {}

        for node in graph_view.nodes.values():
            attrs = node.attributes
            if "http_method" in attrs and "route_path" in attrs:
                method = str(attrs["http_method"]).upper()
                path = str(attrs["route_path"])
                key = f"{method}:{path}"

                if key in route_map and not allow_duplicate_routes:
                    raise DuplicateRouteError(f"Duplicate API route '{key}' detected for handler '{node.node_id}'.")

                record = APIRouteRecord(
                    http_method=method,
                    route_path=path,
                    handler_node=node,
                    controller_name=str(attrs.get("controller", "")),
                    decorators=tuple(attrs.get("decorators", [])),
                )
                route_map[key] = record

        idx = APIRouteIndex(
            index_id=f"idx_route_{uuid.uuid4().hex[:8]}",
            descriptor=desc,
            metadata=meta,
            statistics=stats,
            graph_identity=graph_view.metadata.identity,
            route_map=route_map,
        )
        self._validate_or_raise(idx)
        return idx

    def build_symbol_reference_index(self, graph_view: GraphView) -> SymbolReferenceIndex:
        desc = self._descriptor or IndexDescriptor(name="SymbolReferenceIndex", index_type="SEMANTIC")
        meta = self._metadata or IndexMetadata(source_graph_version=graph_view.metadata.graph_version)
        stats = self._statistics or IndexStatistics(node_count=len(graph_view.nodes))

        def_to_refs: dict[NodeId, list[ImmutableNodeView]] = {}

        for edge in graph_view.edges.values():
            if edge.relationship_type in (RelationshipType.REFERENCES, RelationshipType.CALLS, RelationshipType.USES):
                caller_node = graph_view.nodes.get(edge.source_node_id)
                def_node = graph_view.nodes.get(edge.target_node_id)
                if caller_node and def_node:
                    if def_node.node_id not in def_to_refs:
                        def_to_refs[def_node.node_id] = []
                    def_to_refs[def_node.node_id].append(caller_node)

        idx = SymbolReferenceIndex(
            index_id=f"idx_ref_{uuid.uuid4().hex[:8]}",
            descriptor=desc,
            metadata=meta,
            statistics=stats,
            graph_identity=graph_view.metadata.identity,
            def_to_references={k: tuple(v) for k, v in def_to_refs.items()},
        )
        self._validate_or_raise(idx)
        return idx

    def build_import_index(self, graph_view: GraphView) -> ImportIndex:
        desc = self._descriptor or IndexDescriptor(name="ImportIndex", index_type="SEMANTIC")
        meta = self._metadata or IndexMetadata(source_graph_version=graph_view.metadata.graph_version)
        stats = self._statistics or IndexStatistics(node_count=len(graph_view.nodes))

        file_imports: dict[FileId, list[ImmutableNodeView]] = {}
        pkg_imports: dict[PackageId, list[FileId]] = {}

        for edge in graph_view.edges.values():
            if edge.relationship_type == RelationshipType.IMPORTS:
                importing_node = graph_view.nodes.get(edge.source_node_id)
                imported_node = graph_view.nodes.get(edge.target_node_id)
                if importing_node and imported_node and importing_node.file:
                    fid = importing_node.file
                    if fid not in file_imports:
                        file_imports[fid] = []
                    file_imports[fid].append(imported_node)

                    if imported_node.package:
                        pid = imported_node.package
                        if pid not in pkg_imports:
                            pkg_imports[pid] = []
                        if fid not in pkg_imports[pid]:
                            pkg_imports[pid].append(fid)

        idx = ImportIndex(
            index_id=f"idx_imp_{uuid.uuid4().hex[:8]}",
            descriptor=desc,
            metadata=meta,
            statistics=stats,
            graph_identity=graph_view.metadata.identity,
            file_to_imports={k: tuple(v) for k, v in file_imports.items()},
            imported_packages={k: tuple(v) for k, v in pkg_imports.items()},
        )
        self._validate_or_raise(idx)
        return idx

    def build_module_index(self, graph_view: GraphView) -> ModuleIndex:
        desc = self._descriptor or IndexDescriptor(name="ModuleIndex", index_type="SEMANTIC")
        meta = self._metadata or IndexMetadata(source_graph_version=graph_view.metadata.graph_version)
        stats = self._statistics or IndexStatistics(node_count=len(graph_view.nodes))

        mod_files: dict[str, list[FileId]] = {}
        mod_symbols: dict[str, list[ImmutableNodeView]] = {}

        for node in graph_view.nodes.values():
            mod_name = node.namespace if node.namespace else "global"
            if mod_name not in mod_symbols:
                mod_symbols[mod_name] = []
            mod_symbols[mod_name].append(node)

            if node.file:
                if mod_name not in mod_files:
                    mod_files[mod_name] = []
                if node.file not in mod_files[mod_name]:
                    mod_files[mod_name].append(node.file)

        idx = ModuleIndex(
            index_id=f"idx_mod_{uuid.uuid4().hex[:8]}",
            descriptor=desc,
            metadata=meta,
            statistics=stats,
            graph_identity=graph_view.metadata.identity,
            module_files={k: tuple(v) for k, v in mod_files.items()},
            module_symbols={k: tuple(v) for k, v in mod_symbols.items()},
        )
        self._validate_or_raise(idx)
        return idx

    def build_language_index(self, graph_view: GraphView) -> LanguageIndex:
        desc = self._descriptor or IndexDescriptor(name="LanguageIndex", index_type="SEMANTIC")
        meta = self._metadata or IndexMetadata(source_graph_version=graph_view.metadata.graph_version)
        stats = self._statistics or IndexStatistics(node_count=len(graph_view.nodes))

        lang_files: dict[LanguageId, list[FileId]] = {}
        lang_symbols: dict[LanguageId, list[ImmutableNodeView]] = {}

        for node in graph_view.nodes.values():
            lid = node.language if node.language else LanguageId("python")
            if lid not in lang_symbols:
                lang_symbols[lid] = []
            lang_symbols[lid].append(node)

            if node.file:
                if lid not in lang_files:
                    lang_files[lid] = []
                if node.file not in lang_files[lid]:
                    lang_files[lid].append(node.file)

        idx = LanguageIndex(
            index_id=f"idx_lang_{uuid.uuid4().hex[:8]}",
            descriptor=desc,
            metadata=meta,
            statistics=stats,
            graph_identity=graph_view.metadata.identity,
            lang_files={k: tuple(v) for k, v in lang_files.items()},
            lang_symbols={k: tuple(v) for k, v in lang_symbols.items()},
        )
        self._validate_or_raise(idx)
        return idx

    def build_annotation_index(self, graph_view: GraphView) -> AnnotationIndex:
        desc = self._descriptor or IndexDescriptor(name="AnnotationIndex", index_type="SEMANTIC")
        meta = self._metadata or IndexMetadata(source_graph_version=graph_view.metadata.graph_version)
        stats = self._statistics or IndexStatistics(node_count=len(graph_view.nodes))

        ann_map: dict[str, list[ImmutableNodeView]] = {}

        for node in graph_view.nodes.values():
            decs = node.attributes.get("decorators", [])
            for dec in decs:
                clean_dec = str(dec).strip()
                if not clean_dec.startswith("@"):
                    clean_dec = f"@{clean_dec}"
                if clean_dec not in ann_map:
                    ann_map[clean_dec] = []
                ann_map[clean_dec].append(node)

        idx = AnnotationIndex(
            index_id=f"idx_ann_{uuid.uuid4().hex[:8]}",
            descriptor=desc,
            metadata=meta,
            statistics=stats,
            graph_identity=graph_view.metadata.identity,
            annotation_map={k: tuple(v) for k, v in ann_map.items()},
        )
        self._validate_or_raise(idx)
        return idx

    def build_attribute_index(self, graph_view: GraphView) -> AttributeIndex:
        desc = self._descriptor or IndexDescriptor(name="AttributeIndex", index_type="SEMANTIC")
        meta = self._metadata or IndexMetadata(source_graph_version=graph_view.metadata.graph_version)
        stats = self._statistics or IndexStatistics(node_count=len(graph_view.nodes))

        attr_map: dict[str, list[ImmutableNodeView]] = {
            "public": [],
            "private": [],
            "protected": [],
            "async": [],
            "static": [],
            "deprecated": [],
            "test": [],
            "readonly": [],
        }

        for node in graph_view.nodes.values():
            node_attrs = {str(k).lower(): str(v).lower() for k, v in node.attributes.items()}
            visibility = node_attrs.get("visibility", "public")
            if visibility in attr_map:
                attr_map[visibility].append(node)

            if node_attrs.get("is_async") == "true" or "async" in node.name:
                attr_map["async"].append(node)
            if node_attrs.get("is_static") == "true":
                attr_map["static"].append(node)
            if node_attrs.get("is_test") == "true" or "test" in node.name.lower():
                attr_map["test"].append(node)

        idx = AttributeIndex(
            index_id=f"idx_attr_{uuid.uuid4().hex[:8]}",
            descriptor=desc,
            metadata=meta,
            statistics=stats,
            graph_identity=graph_view.metadata.identity,
            attribute_map={k: tuple(v) for k, v in attr_map.items()},
        )
        self._validate_or_raise(idx)
        return idx

    def build_from_view(self, graph_view: GraphView) -> BaseIndex:
        return self.build_node_index(graph_view)

    def _validate_or_raise(self, index: BaseIndex) -> None:
        report = IndexValidator.validate(index)
        if not report.is_valid:
            errs = "; ".join(f"[{v.category}:{v.rule_name}] {v.message}" for v in report.violations)
            raise ValidationError(f"Index validation failed: {errs}")


__all__ = ["IndexBuilder"]
