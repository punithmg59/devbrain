"""
core/symbols/interfaces.py
---------------------------
Public Interface Protocols for Symbol domain contracts.
"""

from __future__ import annotations

from typing import Any, Dict, Optional, Protocol, runtime_checkable

from core.symbols.enums import Language, SymbolKind


@runtime_checkable
class ISymbolID(Protocol):
    """Protocol for Symbol Identifiers."""
    @property
    def value(self) -> str: ...


@runtime_checkable
class IQualifiedName(Protocol):
    """Protocol for Qualified Names."""
    @property
    def name(self) -> str: ...
    @property
    def is_root(self) -> bool: ...
    def to_string(self, separator: Optional[str] = None) -> str: ...


@runtime_checkable
class ISymbol(Protocol):
    """Protocol for Canonical Symbol entities."""
    @property
    def id(self) -> ISymbolID: ...
    @property
    def fqn(self) -> IQualifiedName: ...
    @property
    def name(self) -> str: ...
    @property
    def kind(self) -> SymbolKind: ...
    @property
    def language(self) -> Language: ...
    def compute_content_hash(self) -> str: ...
