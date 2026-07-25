"""
core/symbol_extractor/interfaces.py
------------------------------------
Public Interface Protocols for Symbol Extractor contracts.
"""

from __future__ import annotations

from typing import List, Optional, Protocol, runtime_checkable

from core.namespaces.tree import NamespaceTree
from core.symbol_extractor.models import TemporaryExtractionID
from core.symbols.enums import Language, SymbolKind
from core.symbols.ids import NamespaceID
from core.symbols.interfaces import IQualifiedName
from models.parser import ParserResult


@runtime_checkable
class IRawSymbol(Protocol):
    """Protocol for Raw Discovered Symbols."""
    @property
    def temp_id(self) -> TemporaryExtractionID: ...
    @property
    def kind(self) -> SymbolKind: ...
    @property
    def name(self) -> str: ...
    @property
    def qualified_name_candidate(self) -> IQualifiedName: ...
    @property
    def namespace_id(self) -> NamespaceID: ...
    @property
    def language(self) -> Language: ...


@runtime_checkable
class IRawSymbolCollection(Protocol):
    """Protocol for RawSymbolCollection containers."""
    @property
    def repository_id(self) -> str: ...
    @property
    def symbols(self) -> List[IRawSymbol]: ...
    def get_symbol(self, temp_id: TemporaryExtractionID) -> Optional[IRawSymbol]: ...
    def get_symbols_in_namespace(self, namespace_id: NamespaceID) -> List[IRawSymbol]: ...
    def get_symbols_in_file(self, file_path: str) -> List[IRawSymbol]: ...


@runtime_checkable
class ISymbolExtractorFacade(Protocol):
    """Protocol for Symbol Extractor Facade."""
    def extract_symbols(self, parser_results: List[ParserResult], tree: NamespaceTree) -> IRawSymbolCollection: ...
