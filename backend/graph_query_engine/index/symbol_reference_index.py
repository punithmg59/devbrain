"""
SymbolReferenceIndex for Mapping Symbol Definitions to Usages and Declarations.
"""

from typing import Any, Iterable, Mapping
from pydantic import Field

from graph_query_engine.index.semantic_index import SemanticIndex
from graph_query_engine.types import NodeId
from graph_query_engine.view.node_view import ImmutableNodeView


class SymbolReferenceIndex(SemanticIndex):
    """
    Immutable, thread-safe index mapping canonical symbol definition NodeId -> usage/reference NodeIds.
    """
    def_to_references: Mapping[NodeId, tuple[ImmutableNodeView, ...]] = Field(
        default_factory=dict,
        description="Immutable mapping of definition NodeId -> reference/usage ImmutableNodeViews",
    )

    def references(self, definition_id: NodeId | str) -> tuple[ImmutableNodeView, ...]:
        """Returns tuple of reference/usage nodes for definition_id."""
        return self.def_to_references.get(NodeId(str(definition_id)), ())

    def count(self, definition_id: NodeId | str) -> int:
        """Returns count of references for definition_id."""
        return len(self.references(definition_id))

    def lookup(self, key: Any) -> Iterable[ImmutableNodeView]:
        """IGraphView lookup contract implementation."""
        return self.references(str(key))


__all__ = ["SymbolReferenceIndex"]
