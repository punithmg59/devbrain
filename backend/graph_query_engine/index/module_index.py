"""
ModuleIndex for Mapping Module Names to Files, Packages, and Symbols.
"""

from typing import Any, Iterable, Mapping
from pydantic import Field

from graph_query_engine.index.semantic_index import SemanticIndex
from graph_query_engine.types import FileId
from graph_query_engine.view.node_view import ImmutableNodeView


class ModuleIndex(SemanticIndex):
    """
    Immutable, thread-safe index grouping files and symbols by module string.
    """
    module_files: Mapping[str, tuple[FileId, ...]] = Field(
        default_factory=dict,
        description="Immutable mapping of module_name -> tuple of FileIds",
    )
    module_symbols: Mapping[str, tuple[ImmutableNodeView, ...]] = Field(
        default_factory=dict,
        description="Immutable mapping of module_name -> tuple of ImmutableNodeViews",
    )

    def files_in_module(self, module_name: str) -> tuple[FileId, ...]:
        """Returns tuple of FileIds belonging to module_name."""
        return self.module_files.get(module_name, ())

    def symbols_in_module(self, module_name: str) -> tuple[ImmutableNodeView, ...]:
        """Returns tuple of ImmutableNodeViews belonging to module_name."""
        return self.module_symbols.get(module_name, ())

    def modules(self) -> tuple[str, ...]:
        """Returns tuple of all indexed module names."""
        return tuple(self.module_files.keys())

    def lookup(self, key: Any) -> Iterable[ImmutableNodeView]:
        """IGraphView lookup contract implementation."""
        return self.symbols_in_module(str(key))


__all__ = ["ModuleIndex"]
