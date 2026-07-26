"""
FileIndex for Deterministic O(1) Lookup of Nodes Belonging to a File.
"""

from typing import Any, Iterable, Mapping, Optional
from pydantic import Field

from graph_query_engine.errors import IndexLookupError
from graph_query_engine.index.lookup_index import LookupIndex
from graph_query_engine.types import FileId
from graph_query_engine.view.node_view import ImmutableNodeView


class FileIndex(LookupIndex):
    """
    Immutable, thread-safe index grouping nodes by FileId.
    """
    file_map: Mapping[FileId, tuple[ImmutableNodeView, ...]] = Field(
        default_factory=dict,
        description="Immutable mapping of FileId -> tuple of ImmutableNodeView",
    )

    def contains(self, file_id: FileId | str) -> bool:
        """Returns True if file_id exists in the index."""
        return FileId(str(file_id)) in self.file_map

    def get(self, file_id: FileId | str) -> tuple[ImmutableNodeView, ...]:
        """
        Retrieves tuple of nodes contained in file_id. Raises IndexLookupError if missing.
        """
        fid = FileId(str(file_id))
        nodes = self.file_map.get(fid)
        if nodes is None:
            raise IndexLookupError(f"FileId '{file_id}' not found in FileIndex.")
        return nodes

    def try_get(self, file_id: FileId | str) -> Optional[tuple[ImmutableNodeView, ...]]:
        """Retrieves tuple of nodes contained in file_id or returns None."""
        return self.file_map.get(FileId(str(file_id)))

    def lookup(self, key: Any) -> Iterable[ImmutableNodeView]:
        """IGraphView lookup contract implementation."""
        return self.try_get(str(key)) or ()

    def files(self) -> tuple[FileId, ...]:
        """Returns tuple of all indexed FileIds."""
        return tuple(self.file_map.keys())

    def count(self) -> int:
        """Returns the total number of indexed files."""
        return len(self.file_map)


__all__ = ["FileIndex"]
