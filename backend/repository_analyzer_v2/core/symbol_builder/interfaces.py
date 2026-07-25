"""
core/symbol_builder/interfaces.py
----------------------------------
Public Interface Protocols for Symbol Builder Facade contracts.
"""

from __future__ import annotations

from typing import Any, List, Optional, Protocol, runtime_checkable

from core.symbol_identity import CanonicalSymbol
from core.symbols import SymbolID
from core.symbols.interfaces import IQualifiedName
from models.parser import ParserResult


@runtime_checkable
class ISemanticRepository(Protocol):
    """Protocol for SemanticRepository Container."""
    @property
    def repository_id(self) -> str: ...
    def get_symbol(self, id: SymbolID) -> Optional[CanonicalSymbol]: ...
    def get_by_fqn(self, fqn: str | IQualifiedName) -> Optional[CanonicalSymbol]: ...
    def get_symbols_in_file(self, file_path: str) -> List[CanonicalSymbol]: ...
    def is_valid(self) -> bool: ...


@runtime_checkable
class ISymbolBuilderFacade(Protocol):
    """Protocol for Symbol Builder Facade."""
    def build(
        self,
        workspace: Optional[Any],
        parser_results: List[ParserResult],
        repository_id: Optional[str] = None
    ) -> ISemanticRepository: ...
