"""
ImportIndex for Mapping Files to Imported Symbols, Modules, and Packages.
"""

from typing import Any, Iterable, Mapping
from pydantic import Field

from graph_query_engine.index.semantic_index import SemanticIndex
from graph_query_engine.types import FileId, PackageId
from graph_query_engine.view.node_view import ImmutableNodeView


class ImportIndex(SemanticIndex):
    """
    Immutable, thread-safe index tracking import dependencies across files, packages, and symbols.
    """
    file_to_imports: Mapping[FileId, tuple[ImmutableNodeView, ...]] = Field(
        default_factory=dict,
        description="Immutable mapping of FileId -> imported ImmutableNodeViews",
    )
    imported_packages: Mapping[PackageId, tuple[FileId, ...]] = Field(
        default_factory=dict,
        description="Immutable mapping of PackageId -> importing FileIds",
    )

    def imports_by_file(self, file_id: FileId | str) -> tuple[ImmutableNodeView, ...]:
        """Returns tuple of imported symbol nodes for file_id."""
        return self.file_to_imports.get(FileId(str(file_id)), ())

    def files_importing_package(self, package_id: PackageId | str) -> tuple[FileId, ...]:
        """Returns tuple of FileIds that import package_id."""
        return self.imported_packages.get(PackageId(str(package_id)), ())

    def lookup(self, key: Any) -> Iterable[ImmutableNodeView]:
        """IGraphView lookup contract implementation."""
        return self.imports_by_file(str(key))


__all__ = ["ImportIndex"]
