"""
Graph Query Engine Index Infrastructure Package.
"""

from graph_query_engine.index.annotation_index import AnnotationIndex
from graph_query_engine.index.api_route_index import APIRouteIndex, APIRouteRecord
from graph_query_engine.index.attribute_index import AttributeIndex
from graph_query_engine.index.base import BaseIndex
from graph_query_engine.index.benchmark_suite import IndexBenchmarkSuite
from graph_query_engine.index.builder import IndexBuilder
from graph_query_engine.index.consistency_checker import IndexConsistencyChecker
from graph_query_engine.index.contracts import (
    IIndex,
    IIndexBuilder,
    IIndexDescriptor,
    IIndexFactory,
    IIndexLifecycle,
    IIndexMetadata,
    IIndexProvider,
    IIndexRegistry,
    IIndexStatistics,
    IIndexValidator,
)
from graph_query_engine.index.csr_adjacency_index import CSRAdjacencyIndex
from graph_query_engine.index.descriptor import IndexDescriptor
from graph_query_engine.index.diagnostics import DiagnosticItem, DiagnosticSeverity, IndexDiagnostics
from graph_query_engine.index.edge_index import EdgeIndex
from graph_query_engine.index.factory import IndexFactory
from graph_query_engine.index.file_index import FileIndex
from graph_query_engine.index.freeze_validator import IndexFreezeValidator
from graph_query_engine.index.health_report import HealthStatus, IndexHealthReport, IndexPerformanceReport
from graph_query_engine.index.import_index import ImportIndex
from graph_query_engine.index.incoming_relationship_index import IncomingRelationshipIndex
from graph_query_engine.index.inheritance_index import InheritanceIndex
from graph_query_engine.index.integrity_checker import IndexIntegrityChecker
from graph_query_engine.index.interface_implementation_index import InterfaceImplementationIndex
from graph_query_engine.index.language_index import LanguageIndex
from graph_query_engine.index.lifecycle import (
    IndexLifecycle,
    IndexLifecycleState,
    IndexLifecycleStatus,
)
from graph_query_engine.index.lookup_index import LookupIndex
from graph_query_engine.index.manifest import IndexManifest
from graph_query_engine.index.memory_report import IndexMemoryReport
from graph_query_engine.index.metadata import IndexMetadata
from graph_query_engine.index.metrics import IndexMetrics, IndexStatisticsCollector
from graph_query_engine.index.module_index import ModuleIndex
from graph_query_engine.index.namespace_index import NamespaceIndex
from graph_query_engine.index.node_index import NodeIndex
from graph_query_engine.index.node_relationship_index import NodeRelationshipIndex
from graph_query_engine.index.outgoing_relationship_index import OutgoingRelationshipIndex
from graph_query_engine.index.package_index import PackageIndex
from graph_query_engine.index.provider import IndexProvider
from graph_query_engine.index.qualified_name_index import QualifiedNameIndex
from graph_query_engine.index.registry import IndexRegistry
from graph_query_engine.index.relationship_base_index import RelationshipBaseIndex
from graph_query_engine.index.relationship_index import RelationshipIndex
from graph_query_engine.index.relationship_type_index import RelationshipTypeIndex
from graph_query_engine.index.reverse_csr_adjacency_index import ReverseCSRAdjacencyIndex
from graph_query_engine.index.self_loop_index import SelfLoopIndex
from graph_query_engine.index.semantic_index import SemanticIndex
from graph_query_engine.index.semantic_registry import SemanticIndexRegistry
from graph_query_engine.index.snapshot import IndexSnapshot
from graph_query_engine.index.statistics import IndexStatistics
from graph_query_engine.index.symbol_index import SymbolIndex
from graph_query_engine.index.symbol_reference_index import SymbolReferenceIndex
from graph_query_engine.index.type_hierarchy_index import TypeHierarchyIndex
from graph_query_engine.index.validation import (
    IndexValidationReport,
    IndexValidationViolation,
    IndexValidator,
)
from graph_query_engine.index.validation_engine import IndexValidationEngine

__all__ = [
    # Hierarchy Base Classes
    "BaseIndex",
    "LookupIndex",
    "RelationshipBaseIndex",
    "SemanticIndex",
    "SemanticIndexRegistry",
    # Step 3.2 Concrete Lookup Indexes
    "NodeIndex",
    "EdgeIndex",
    "SymbolIndex",
    "FileIndex",
    "PackageIndex",
    "NamespaceIndex",
    "QualifiedNameIndex",
    # Step 3.3 Concrete Relationship Indexes
    "CSRAdjacencyIndex",
    "ReverseCSRAdjacencyIndex",
    "RelationshipIndex",
    "OutgoingRelationshipIndex",
    "IncomingRelationshipIndex",
    "NodeRelationshipIndex",
    "RelationshipTypeIndex",
    "SelfLoopIndex",
    # Step 3.4 Concrete Semantic Indexes
    "TypeHierarchyIndex",
    "InheritanceIndex",
    "InterfaceImplementationIndex",
    "APIRouteRecord",
    "APIRouteIndex",
    "SymbolReferenceIndex",
    "ImportIndex",
    "ModuleIndex",
    "LanguageIndex",
    "AnnotationIndex",
    "AttributeIndex",
    # Step 3.5 Hardening, Reporting & Freeze Infrastructure
    "IndexValidationEngine",
    "IndexConsistencyChecker",
    "IndexIntegrityChecker",
    "IndexFreezeValidator",
    "IndexDiagnostics",
    "DiagnosticItem",
    "DiagnosticSeverity",
    "IndexHealthReport",
    "HealthStatus",
    "IndexPerformanceReport",
    "IndexMemoryReport",
    "IndexSnapshot",
    "IndexManifest",
    "IndexMetrics",
    "IndexStatisticsCollector",
    "IndexBenchmarkSuite",
    # Infrastructure Models
    "IndexDescriptor",
    "IndexMetadata",
    "IndexStatistics",
    "IndexLifecycle",
    "IndexLifecycleState",
    "IndexLifecycleStatus",
    "IndexValidator",
    "IndexValidationReport",
    "IndexValidationViolation",
    "IndexBuilder",
    "IndexFactory",
    "IndexRegistry",
    "IndexProvider",
    # Protocols
    "IIndex",
    "IIndexBuilder",
    "IIndexRegistry",
    "IIndexFactory",
    "IIndexLifecycle",
    "IIndexStatistics",
    "IIndexValidator",
    "IIndexMetadata",
    "IIndexDescriptor",
    "IIndexProvider",
]
