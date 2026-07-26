"""
SemanticIndexRegistry for Managing Repository Semantic Indexes.
"""

import threading
from typing import Mapping, Optional, Type

from graph_query_engine.index.annotation_index import AnnotationIndex
from graph_query_engine.index.api_route_index import APIRouteIndex
from graph_query_engine.index.attribute_index import AttributeIndex
from graph_query_engine.index.import_index import ImportIndex
from graph_query_engine.index.inheritance_index import InheritanceIndex
from graph_query_engine.index.interface_implementation_index import InterfaceImplementationIndex
from graph_query_engine.index.language_index import LanguageIndex
from graph_query_engine.index.module_index import ModuleIndex
from graph_query_engine.index.semantic_index import SemanticIndex
from graph_query_engine.index.symbol_reference_index import SymbolReferenceIndex
from graph_query_engine.index.type_hierarchy_index import TypeHierarchyIndex


class SemanticIndexRegistry:
    """
    Thread-safe registry dedicated to managing SemanticIndex implementation types and active instances.
    """

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._semantic_classes: dict[str, Type[SemanticIndex]] = {
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
        self._active_indexes: dict[str, SemanticIndex] = {}

    def register_type(self, name: str, index_cls: Type[SemanticIndex]) -> None:
        """Registers a SemanticIndex class under name."""
        with self._lock:
            self._semantic_classes[name] = index_cls

    def register_instance(self, index: SemanticIndex) -> None:
        """Registers an active SemanticIndex instance."""
        with self._lock:
            self._active_indexes[index.index_name] = index

    def get_index(self, name: str) -> Optional[SemanticIndex]:
        """Retrieves active SemanticIndex instance by name."""
        with self._lock:
            return self._active_indexes.get(name)

    def contains(self, name: str) -> bool:
        """Checks if a semantic index type or active instance is registered."""
        with self._lock:
            return name in self._active_indexes or name in self._semantic_classes

    def has_index(self, name: str) -> bool:
        """Checks if an active semantic index instance is registered."""
        with self._lock:
            return name in self._active_indexes

    def list_indexes(self) -> tuple[str, ...]:
        """Returns tuple of active semantic index names."""
        with self._lock:
            return tuple(self._active_indexes.keys())

    def get_registered_types(self) -> Mapping[str, Type[SemanticIndex]]:
        """Returns read-only mapping of registered semantic index types."""
        with self._lock:
            return dict(self._semantic_classes)


__all__ = ["SemanticIndexRegistry"]
