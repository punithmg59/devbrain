"""
PackageIndex for Deterministic O(1) Lookup of Nodes by PackageId.
"""

from typing import Any, Iterable, Mapping, Optional
from pydantic import Field

from graph_query_engine.errors import IndexLookupError
from graph_query_engine.index.lookup_index import LookupIndex
from graph_query_engine.types import PackageId
from graph_query_engine.view.node_view import ImmutableNodeView


class PackageIndex(LookupIndex):
    """
    Immutable, thread-safe index grouping nodes by PackageId.
    """
    package_map: Mapping[PackageId, tuple[ImmutableNodeView, ...]] = Field(
        default_factory=dict,
        description="Immutable mapping of PackageId -> tuple of ImmutableNodeView",
    )

    def contains(self, package_id: PackageId | str) -> bool:
        """Returns True if package_id exists in the index."""
        return PackageId(str(package_id)) in self.package_map

    def get(self, package_id: PackageId | str) -> tuple[ImmutableNodeView, ...]:
        """
        Retrieves tuple of nodes in package_id. Raises IndexLookupError if missing.
        """
        pid = PackageId(str(package_id))
        nodes = self.package_map.get(pid)
        if nodes is None:
            raise IndexLookupError(f"PackageId '{package_id}' not found in PackageIndex.")
        return nodes

    def try_get(self, package_id: PackageId | str) -> Optional[tuple[ImmutableNodeView, ...]]:
        """Retrieves tuple of nodes in package_id or returns None."""
        return self.package_map.get(PackageId(str(package_id)))

    def lookup(self, key: Any) -> Iterable[ImmutableNodeView]:
        """IGraphView lookup contract implementation."""
        return self.try_get(str(key)) or ()

    def packages(self) -> tuple[PackageId, ...]:
        """Returns tuple of all indexed PackageIds."""
        return tuple(self.package_map.keys())

    def count(self) -> int:
        """Returns the total number of indexed packages."""
        return len(self.package_map)


__all__ = ["PackageIndex"]
