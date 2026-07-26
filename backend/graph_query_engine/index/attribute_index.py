"""
AttributeIndex for Indexing Symbols by Access Modifiers and Attribute Flags (public, private, async, static, etc.).
"""

from typing import Any, Iterable, Mapping
from pydantic import Field

from graph_query_engine.index.semantic_index import SemanticIndex
from graph_query_engine.view.node_view import ImmutableNodeView


class AttributeIndex(SemanticIndex):
    """
    Immutable, thread-safe index grouping symbols by modifier attribute flag (public, private, async, static, test, etc.).
    """
    attribute_map: Mapping[str, tuple[ImmutableNodeView, ...]] = Field(
        default_factory=dict,
        description="Immutable mapping of attribute flag string -> tuple of ImmutableNodeViews",
    )

    def by_attribute(self, attribute: str) -> tuple[ImmutableNodeView, ...]:
        """Returns tuple of nodes possessing attribute flag."""
        return self.attribute_map.get(attribute.lower(), ())

    def public_symbols(self) -> tuple[ImmutableNodeView, ...]:
        """Returns tuple of public symbols."""
        return self.by_attribute("public")

    def private_symbols(self) -> tuple[ImmutableNodeView, ...]:
        """Returns tuple of private symbols."""
        return self.by_attribute("private")

    def async_symbols(self) -> tuple[ImmutableNodeView, ...]:
        """Returns tuple of async symbols."""
        return self.by_attribute("async")

    def static_symbols(self) -> tuple[ImmutableNodeView, ...]:
        """Returns tuple of static symbols."""
        return self.by_attribute("static")

    def test_symbols(self) -> tuple[ImmutableNodeView, ...]:
        """Returns tuple of test symbols."""
        return self.by_attribute("test")

    def attributes(self) -> tuple[str, ...]:
        """Returns tuple of all indexed attribute flags."""
        return tuple(self.attribute_map.keys())

    def lookup(self, key: Any) -> Iterable[ImmutableNodeView]:
        """IGraphView lookup contract implementation."""
        return self.by_attribute(str(key))


__all__ = ["AttributeIndex"]
