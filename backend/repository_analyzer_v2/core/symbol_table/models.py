"""
core/symbol_table/models.py
----------------------------
SymbolTable and SymbolTableStatistics Domain Models.
"""

from __future__ import annotations

from typing import Iterator, List, Optional, Union
from pydantic import BaseModel, Field

from core.symbol_identity import CanonicalSymbol
from core.symbol_table.diagnostics import SymbolTableDiagnostics
from core.symbol_table.indexes import SymbolIndexSet
from core.symbol_table.queries import SymbolTableQueryEngine
from core.symbols import Language, QualifiedName, SymbolID, SymbolKind, VisibilityKind
from core.symbols.ids import NamespaceID


class SymbolTableStatistics(BaseModel):
    """Execution and indexing statistics for SymbolTable."""
    total_symbols: int = Field(default=0, ge=0)
    total_indexed_fqns: int = Field(default=0, ge=0)
    total_files: int = Field(default=0, ge=0)
    total_namespaces: int = Field(default=0, ge=0)
    duration_ms: float = Field(default=0.0, ge=0.0)

    model_config = {
        "frozen": True
    }


class SymbolTable(BaseModel):
    """
    Canonical, Immutable SymbolTable Container.
    
    Serves as the frozen input contract produced by Step 3.5 and consumed by Step 3.6.
    """
    repository_id: str = Field(..., description="Repository identifier")
    indexes: SymbolIndexSet = Field(default_factory=SymbolIndexSet, description="Multi-dimensional lookup indexes")
    statistics: SymbolTableStatistics = Field(default_factory=SymbolTableStatistics, description="Indexing statistics")
    diagnostics: SymbolTableDiagnostics = Field(default_factory=SymbolTableDiagnostics, description="Diagnostics report")

    model_config = {
        "frozen": True,
        "arbitrary_types_allowed": True
    }

    def get_by_symbol_id(self, id: Union[SymbolID, str]) -> Optional[CanonicalSymbol]:
        """O(1) lookup by SymbolID object or string."""
        return SymbolTableQueryEngine.get_by_symbol_id(self, id)

    def get_by_qualified_name(self, fqn: Union[str, QualifiedName]) -> Optional[CanonicalSymbol]:
        """O(1) lookup by QualifiedName object or string."""
        return SymbolTableQueryEngine.get_by_qualified_name(self, fqn)

    def get_by_name(self, name: str) -> List[CanonicalSymbol]:
        """Fetch all symbols sharing an unqualified simple name."""
        return SymbolTableQueryEngine.get_by_name(self, name)

    def get_namespace_symbols(self, namespace_id: Union[NamespaceID, str]) -> List[CanonicalSymbol]:
        """Fetch all symbols contained in a specific NamespaceID."""
        return SymbolTableQueryEngine.get_namespace_symbols(self, namespace_id)

    def get_file_symbols(self, file_path: str) -> List[CanonicalSymbol]:
        """Fetch all symbols declared inside a specific file."""
        return SymbolTableQueryEngine.get_file_symbols(self, file_path)

    def get_language_symbols(self, language: Union[Language, str]) -> List[CanonicalSymbol]:
        """Fetch all symbols for a target programming language."""
        return SymbolTableQueryEngine.get_language_symbols(self, language)

    def get_symbols_by_kind(self, kind: Union[SymbolKind, str]) -> List[CanonicalSymbol]:
        """Fetch all symbols matching a specific SymbolKind."""
        return SymbolTableQueryEngine.get_symbols_by_kind(self, kind)

    def get_visible_symbols(self, visibility: Union[VisibilityKind, str]) -> List[CanonicalSymbol]:
        """Fetch all symbols matching a specific VisibilityKind."""
        return SymbolTableQueryEngine.get_visible_symbols(self, visibility)

    def contains(self, key: Union[SymbolID, str, QualifiedName]) -> bool:
        """True if SymbolID or FQN exists in the SymbolTable."""
        return SymbolTableQueryEngine.contains(self, key)

    def exists(self, fqn: Union[str, QualifiedName]) -> bool:
        """True if QualifiedName exists in the SymbolTable."""
        return SymbolTableQueryEngine.exists(self, fqn)

    def count(self) -> int:
        """Total count of canonical symbols indexed."""
        return SymbolTableQueryEngine.count(self)

    def iterate(self) -> Iterator[CanonicalSymbol]:
        """Iterator over all canonical symbols in the SymbolTable."""
        return SymbolTableQueryEngine.iterate(self)
