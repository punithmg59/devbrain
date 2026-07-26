"""
QualifiedNameIndex for Deterministic Case-Sensitive O(1) Lookup by Qualified Name.
"""

from typing import Any, Iterable, Mapping, Optional
from pydantic import Field

from graph_query_engine.errors import IndexLookupError
from graph_query_engine.index.lookup_index import LookupIndex
from graph_query_engine.view.node_view import ImmutableNodeView


class QualifiedNameIndex(LookupIndex):
    """
    Immutable, thread-safe index providing O(1) exact lookups by fully qualified symbol string.
    """
    name_map: Mapping[str, ImmutableNodeView] = Field(
        default_factory=dict,
        description="Immutable mapping of qualified_name string -> ImmutableNodeView",
    )

    def contains(self, qualified_name: str) -> bool:
        """Returns True if qualified_name exists in the index."""
        return qualified_name in self.name_map

    def get(self, qualified_name: str) -> ImmutableNodeView:
        """
        Retrieves ImmutableNodeView by qualified_name. Raises IndexLookupError if missing.
        """
        node = self.name_map.get(qualified_name)
        if node is None:
            raise IndexLookupError(f"Qualified name '{qualified_name}' not found in QualifiedNameIndex.")
        return node

    def try_get(self, qualified_name: str) -> Optional[ImmutableNodeView]:
        """Retrieves ImmutableNodeView by qualified_name or returns None."""
        return self.name_map.get(qualified_name)

    def lookup(self, key: Any) -> Iterable[ImmutableNodeView]:
        """IGraphView lookup contract implementation."""
        res = self.try_get(str(key))
        return (res,) if res is not None else ()

    def names(self) -> tuple[str, ...]:
        """Returns tuple of all indexed qualified names."""
        return tuple(self.name_map.keys())

    def count(self) -> int:
        """Returns the total number of indexed qualified names."""
        return len(self.name_map)


__all__ = ["QualifiedNameIndex"]
