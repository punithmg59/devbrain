"""
SymbolIndex for Deterministic O(1) Lookup by SymbolId.
"""

from typing import Any, Iterable, Mapping, Optional
from pydantic import Field

from graph_query_engine.errors import IndexLookupError
from graph_query_engine.index.lookup_index import LookupIndex
from graph_query_engine.types import SymbolId
from graph_query_engine.view.node_view import ImmutableNodeView


class SymbolIndex(LookupIndex):
    """
    Immutable, thread-safe index providing O(1) lookups over canonical symbols by SymbolId.
    """
    symbol_map: Mapping[SymbolId, ImmutableNodeView] = Field(
        default_factory=dict,
        description="Immutable mapping of SymbolId -> ImmutableNodeView",
    )

    def contains(self, symbol_id: SymbolId | str) -> bool:
        """Returns True if symbol_id exists in the index."""
        return SymbolId(str(symbol_id)) in self.symbol_map

    def get(self, symbol_id: SymbolId | str) -> ImmutableNodeView:
        """
        Retrieves ImmutableNodeView by SymbolId. Raises IndexLookupError if missing.
        """
        sid = SymbolId(str(symbol_id))
        node = self.symbol_map.get(sid)
        if node is None:
            raise IndexLookupError(f"SymbolId '{symbol_id}' not found in SymbolIndex.")
        return node

    def try_get(self, symbol_id: SymbolId | str) -> Optional[ImmutableNodeView]:
        """Retrieves ImmutableNodeView by SymbolId or returns None."""
        return self.symbol_map.get(SymbolId(str(symbol_id)))

    def lookup(self, key: Any) -> Iterable[ImmutableNodeView]:
        """IGraphView lookup contract implementation."""
        res = self.try_get(str(key))
        return (res,) if res is not None else ()

    def symbols(self) -> tuple[SymbolId, ...]:
        """Returns tuple of all indexed SymbolIds."""
        return tuple(self.symbol_map.keys())

    def count(self) -> int:
        """Returns the total number of indexed symbols."""
        return len(self.symbol_map)


__all__ = ["SymbolIndex"]
