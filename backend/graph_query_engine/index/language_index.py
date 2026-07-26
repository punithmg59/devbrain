"""
LanguageIndex for Grouping Files and Symbols by Primary Language (Python, Java, TypeScript, Go, Rust).
"""

from typing import Any, Iterable, Mapping
from pydantic import Field

from graph_query_engine.index.semantic_index import SemanticIndex
from graph_query_engine.types import FileId, LanguageId
from graph_query_engine.view.node_view import ImmutableNodeView


class LanguageIndex(SemanticIndex):
    """
    Immutable, thread-safe index grouping files and symbols by primary LanguageId.
    """
    lang_files: Mapping[LanguageId, tuple[FileId, ...]] = Field(
        default_factory=dict,
        description="Immutable mapping of LanguageId -> tuple of FileIds",
    )
    lang_symbols: Mapping[LanguageId, tuple[ImmutableNodeView, ...]] = Field(
        default_factory=dict,
        description="Immutable mapping of LanguageId -> tuple of ImmutableNodeViews",
    )

    def files_by_language(self, language: LanguageId | str) -> tuple[FileId, ...]:
        """Returns tuple of FileIds written in language."""
        lid = LanguageId(str(language).lower())
        return self.lang_files.get(lid, ())

    def symbols_by_language(self, language: LanguageId | str) -> tuple[ImmutableNodeView, ...]:
        """Returns tuple of ImmutableNodeViews written in language."""
        lid = LanguageId(str(language).lower())
        return self.lang_symbols.get(lid, ())

    def languages(self) -> tuple[LanguageId, ...]:
        """Returns tuple of all indexed LanguageIds."""
        return tuple(self.lang_files.keys())

    def lookup(self, key: Any) -> Iterable[ImmutableNodeView]:
        """IGraphView lookup contract implementation."""
        return self.symbols_by_language(str(key))


__all__ = ["LanguageIndex"]
