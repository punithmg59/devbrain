"""
core/call_edges/interfaces.py
------------------------------
Public Interface Protocols for Call Edge Builder.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from core.edges import IEdgeCollection
from core.symbol_builder import ISemanticRepository


@runtime_checkable
class ICallEdgeBuilderFacade(Protocol):
    """Protocol for Call Edge Builder Facade."""
    def build(
        self,
        semantic_repository: ISemanticRepository
    ) -> IEdgeCollection: ...
