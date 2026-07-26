"""
Thread-Safe IndexRegistry for Managing Graph Index Types and Instances.
"""

import threading
from typing import Mapping, Optional, Type

from graph_query_engine.index.annotation_index import AnnotationIndex
from graph_query_engine.index.api_route_index import APIRouteIndex
from graph_query_engine.index.attribute_index import AttributeIndex
from graph_query_engine.index.base import BaseIndex
from graph_query_engine.index.csr_adjacency_index import CSRAdjacencyIndex
from graph_query_engine.index.edge_index import EdgeIndex
from graph_query_engine.index.file_index import FileIndex
from graph_query_engine.index.import_index import ImportIndex
from graph_query_engine.index.incoming_relationship_index import IncomingRelationshipIndex
from graph_query_engine.index.inheritance_index import InheritanceIndex
from graph_query_engine.index.interface_implementation_index import InterfaceImplementationIndex
from graph_query_engine.index.language_index import LanguageIndex
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
from graph_query_engine.index.symbol_index import SymbolIndex
from graph_query_engine.index.symbol_reference_index import SymbolReferenceIndex
from graph_query_engine.index.type_hierarchy_index import TypeHierarchyIndex


class IndexRegistry:
    """
    Thread-safe registry for managing index types and active index instances.
    """

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._index_classes: dict[str, Type[BaseIndex]] = {
            # Step 3.2 Lookup Indexes
            "NodeIndex": NodeIndex,
            "EdgeIndex": EdgeIndex,
            "SymbolIndex": SymbolIndex,
            "FileIndex": FileIndex,
            "PackageIndex": PackageIndex,
            "NamespaceIndex": NamespaceIndex,
            "QualifiedNameIndex": QualifiedNameIndex,
            # Step 3.3 Relationship Indexes
            "CSRAdjacencyIndex": CSRAdjacencyIndex,
            "ReverseCSRAdjacencyIndex": ReverseCSRAdjacencyIndex,
            "RelationshipIndex": RelationshipIndex,
            "OutgoingRelationshipIndex": OutgoingRelationshipIndex,
            "IncomingRelationshipIndex": IncomingRelationshipIndex,
            "NodeRelationshipIndex": NodeRelationshipIndex,
            "RelationshipTypeIndex": RelationshipTypeIndex,
            "SelfLoopIndex": SelfLoopIndex,
            # Step 3.4 Semantic Indexes
            "TypeHierarchyIndex": TypeHierarchyIndex,
            "InheritanceIndex": InheritanceIndex,
            "InterfaceImplementationIndex": InterfaceImplementationIndex,
            "APIRouteIndex": APIRouteIndex,
            "SymbolReferenceIndex": SymbolReferenceIndex,
            "ImportIndex": ImportIndex,
            "ModuleIndex": ModuleIndex,
            "LanguageIndex": LanguageIndex,
            "AnnotationIndex": AnnotationIndex,
            "AttributeIndex": AttributeIndex,
        }
        self._active_indexes: dict[str, BaseIndex] = {}

    def register(self, index_name: str, index_cls: Type[BaseIndex]) -> None:
        """Registers an index implementation class under index_name."""
        with self._lock:
            self._index_classes[index_name] = index_cls

    def register_type(self, index_name: str, index_cls: Type[BaseIndex]) -> None:
        """Alias for register()."""
        self.register(index_name, index_cls)

    def register_instance(self, index: BaseIndex) -> None:
        """Registers an active BaseIndex instance under its descriptor name."""
        with self._lock:
            self._active_indexes[index.index_name] = index

    def get_index(self, index_name: str) -> Optional[BaseIndex]:
        """Retrieves active BaseIndex instance by index_name."""
        with self._lock:
            return self._active_indexes.get(index_name)

    def contains(self, index_name: str) -> bool:
        """Checks if an active index or type is registered."""
        with self._lock:
            return index_name in self._active_indexes or index_name in self._index_classes

    def has_index(self, index_name: str) -> bool:
        """Checks if an active index instance is registered."""
        with self._lock:
            return index_name in self._active_indexes

    def list_indexes(self) -> tuple[str, ...]:
        """Returns tuple of all active index names."""
        with self._lock:
            return tuple(self._active_indexes.keys())

    def list_available_indexes(self) -> tuple[str, ...]:
        """Alias for list_indexes()."""
        return self.list_indexes()

    def get_registered_types(self) -> Mapping[str, Type[BaseIndex]]:
        """Returns read-only mapping of registered index types."""
        with self._lock:
            return dict(self._index_classes)


__all__ = ["IndexRegistry"]
