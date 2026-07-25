"""
core/type_reference_edges/interfaces.py
----------------------------------------
Public Interface Protocols for Type Reference Edge Builder.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from core.edges import IEdgeCollection
from core.symbol_builder import ISemanticRepository


@runtime_checkable
class ITypeReferenceEdgeBuilderFacade(Protocol):
    """Protocol for Type Reference Edge Builder Facade."""
    def build(
        self,
        semantic_repository: ISemanticRepository
    ) -> IEdgeCollection: ...
