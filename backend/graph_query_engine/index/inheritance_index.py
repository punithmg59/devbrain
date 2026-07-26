"""
InheritanceIndex for Fast Lookup of Inherits, Implements, Extends, Abstract, Interface, Trait, and Mixin Modifiers.
"""

from typing import Any, Iterable, Mapping
from pydantic import Field

from graph_query_engine.index.semantic_index import SemanticIndex
from graph_query_engine.types import NodeId
from graph_query_engine.view.node_view import ImmutableNodeView


class InheritanceIndex(SemanticIndex):
    """
    Immutable, thread-safe index categorizing OOP inheritance constructs (abstract, interface, trait, mixin).
    """
    kind_map: Mapping[str, tuple[ImmutableNodeView, ...]] = Field(
        default_factory=dict,
        description="Immutable mapping of OOP modifier kind (abstract, interface, trait, mixin) -> nodes",
    )

    def by_kind(self, kind: str) -> tuple[ImmutableNodeView, ...]:
        """Returns tuple of ImmutableNodeView instances matching inheritance kind."""
        return self.kind_map.get(kind.lower(), ())

    def interfaces(self) -> tuple[ImmutableNodeView, ...]:
        """Returns tuple of all interface type nodes."""
        return self.by_kind("interface")

    def abstract_classes(self) -> tuple[ImmutableNodeView, ...]:
        """Returns tuple of all abstract class nodes."""
        return self.by_kind("abstract")

    def traits(self) -> tuple[ImmutableNodeView, ...]:
        """Returns tuple of all trait nodes."""
        return self.by_kind("trait")

    def mixins(self) -> tuple[ImmutableNodeView, ...]:
        """Returns tuple of all mixin nodes."""
        return self.by_kind("mixin")

    def lookup(self, key: Any) -> Iterable[ImmutableNodeView]:
        """IGraphView lookup contract implementation."""
        return self.by_kind(str(key))


__all__ = ["InheritanceIndex"]
