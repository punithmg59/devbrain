"""
InterfaceImplementationIndex for Mapping Interface NodeIds to Implementing Classes and Vice Versa.
"""

from typing import Any, Iterable, Mapping
from pydantic import Field

from graph_query_engine.index.semantic_index import SemanticIndex
from graph_query_engine.types import NodeId
from graph_query_engine.view.node_view import ImmutableNodeView


class InterfaceImplementationIndex(SemanticIndex):
    """
    Immutable, thread-safe index mapping interface NodeId -> implementing class NodeIds.
    """
    interface_to_implementations: Mapping[NodeId, tuple[ImmutableNodeView, ...]] = Field(
        default_factory=dict,
        description="Immutable mapping of interface NodeId -> implementing class ImmutableNodeViews",
    )
    class_to_interfaces: Mapping[NodeId, tuple[ImmutableNodeView, ...]] = Field(
        default_factory=dict,
        description="Immutable mapping of class NodeId -> interface ImmutableNodeViews",
    )

    def implementations(self, interface_id: NodeId | str) -> tuple[ImmutableNodeView, ...]:
        """Returns tuple of implementing class nodes for interface_id."""
        return self.interface_to_implementations.get(NodeId(str(interface_id)), ())

    def interfaces_for(self, class_id: NodeId | str) -> tuple[ImmutableNodeView, ...]:
        """Returns tuple of interface nodes implemented by class_id."""
        return self.class_to_interfaces.get(NodeId(str(class_id)), ())

    def lookup(self, key: Any) -> Iterable[ImmutableNodeView]:
        """IGraphView lookup contract implementation."""
        return self.implementations(str(key))


__all__ = ["InterfaceImplementationIndex"]
