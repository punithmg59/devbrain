"""
TypeHierarchyIndex for Lookup of Inheritance Hierarchies and Base/Derived Types.
"""

from typing import Any, Iterable, Mapping
from pydantic import Field

from graph_query_engine.index.semantic_index import SemanticIndex
from graph_query_engine.types import NodeId
from graph_query_engine.view.node_view import ImmutableNodeView


class TypeHierarchyIndex(SemanticIndex):
    """
    Immutable, thread-safe index for base/derived class type hierarchies and overrides.
    """
    parent_map: Mapping[NodeId, tuple[ImmutableNodeView, ...]] = Field(
        default_factory=dict,
        description="Immutable mapping of NodeId -> tuple of parent base class ImmutableNodeView",
    )
    child_map: Mapping[NodeId, tuple[ImmutableNodeView, ...]] = Field(
        default_factory=dict,
        description="Immutable mapping of NodeId -> tuple of derived child class ImmutableNodeView",
    )

    def base_classes(self, node_id: NodeId | str) -> tuple[ImmutableNodeView, ...]:
        """Returns tuple of direct base parent types for node_id."""
        return self.parent_map.get(NodeId(str(node_id)), ())

    def derived_classes(self, node_id: NodeId | str) -> tuple[ImmutableNodeView, ...]:
        """Returns tuple of direct derived child types for node_id."""
        return self.child_map.get(NodeId(str(node_id)), ())

    def parents(self, node_id: NodeId | str) -> tuple[ImmutableNodeView, ...]:
        """Alias for base_classes()."""
        return self.base_classes(node_id)

    def children(self, node_id: NodeId | str) -> tuple[ImmutableNodeView, ...]:
        """Alias for derived_classes()."""
        return self.derived_classes(node_id)

    def lookup(self, key: Any) -> Iterable[ImmutableNodeView]:
        """IGraphView lookup contract implementation."""
        return self.base_classes(str(key))


__all__ = ["TypeHierarchyIndex"]
