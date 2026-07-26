"""
NodeIndex for Deterministic O(1) Lookup by NodeId.
"""

from typing import Any, Iterable, Mapping, Optional
from pydantic import Field

from graph_query_engine.errors import IndexLookupError
from graph_query_engine.index.lookup_index import LookupIndex
from graph_query_engine.types import NodeId
from graph_query_engine.view.node_view import ImmutableNodeView


class NodeIndex(LookupIndex):
    """
    Immutable, thread-safe index providing O(1) lookups over graph nodes by NodeId.
    """
    node_map: Mapping[NodeId, ImmutableNodeView] = Field(
        default_factory=dict,
        description="Immutable mapping of NodeId -> ImmutableNodeView",
    )

    def contains(self, node_id: NodeId | str) -> bool:
        """Returns True if node_id exists in the index."""
        return NodeId(str(node_id)) in self.node_map

    def exists(self, node_id: NodeId | str) -> bool:
        """Alias for contains()."""
        return self.contains(node_id)

    def get(self, node_id: NodeId | str) -> ImmutableNodeView:
        """
        Retrieves ImmutableNodeView by NodeId. Raises IndexLookupError if missing.
        """
        nid = NodeId(str(node_id))
        node = self.node_map.get(nid)
        if node is None:
            raise IndexLookupError(f"NodeId '{node_id}' not found in NodeIndex.")
        return node

    def try_get(self, node_id: NodeId | str) -> Optional[ImmutableNodeView]:
        """Retrieves ImmutableNodeView by NodeId or returns None."""
        return self.node_map.get(NodeId(str(node_id)))

    def lookup(self, key: Any) -> Iterable[ImmutableNodeView]:
        """IGraphView lookup contract implementation."""
        res = self.try_get(str(key))
        return (res,) if res is not None else ()

    def size(self) -> int:
        """Returns the total number of indexed nodes."""
        return len(self.node_map)

    def keys(self) -> tuple[NodeId, ...]:
        """Returns tuple of all indexed NodeIds."""
        return tuple(self.node_map.keys())

    def values(self) -> tuple[ImmutableNodeView, ...]:
        """Returns tuple of all indexed ImmutableNodeView instances."""
        return tuple(self.node_map.values())

    def items(self) -> tuple[tuple[NodeId, ImmutableNodeView], ...]:
        """Returns tuple of (NodeId, ImmutableNodeView) pairs."""
        return tuple(self.node_map.items())


__all__ = ["NodeIndex"]
