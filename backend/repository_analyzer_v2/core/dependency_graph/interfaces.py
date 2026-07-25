"""
core/dependency_graph/interfaces.py
------------------------------------
Public Interface Protocols for Dependency Graph Builder.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from core.edges import IEdgeCollection
from core.symbol_builder import ISemanticRepository


@runtime_checkable
class IDependencyGraph(Protocol):
    """Protocol for DependencyGraph."""
    @property
    def repository_id(self) -> str: ...
    @property
    def version(self) -> str: ...


@runtime_checkable
class IDependencyGraphBuilderFacade(Protocol):
    """Protocol for DependencyGraphBuilder Facade."""
    def build(
        self,
        semantic_repository: ISemanticRepository,
        import_edges: IEdgeCollection,
        call_edges: IEdgeCollection,
        inheritance_edges: IEdgeCollection,
        type_reference_edges: IEdgeCollection
    ) -> IDependencyGraph: ...
