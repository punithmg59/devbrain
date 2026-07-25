"""
core/symbol_identity/interfaces.py
-----------------------------------
Public Interface Protocols for Symbol Identity contracts.
"""

from __future__ import annotations

from typing import List, Optional, Protocol, runtime_checkable

from core.namespaces.tree import NamespaceTree
from core.symbol_extractor import RawSymbolCollection
from core.symbols import Language, SymbolID, SymbolKind
from core.symbols.ids import NamespaceID
from core.symbols.interfaces import IQualifiedName


@runtime_checkable
class ICanonicalSymbol(Protocol):
    """Protocol for Canonical Symbols."""
    @property
    def id(self) -> SymbolID: ...
    @property
    def fqn(self) -> IQualifiedName: ...
    @property
    def name(self) -> str: ...
    @property
    def kind(self) -> SymbolKind: ...
    @property
    def namespace_id(self) -> NamespaceID: ...
    @property
    def language(self) -> Language: ...


@runtime_checkable
class ICanonicalSymbolCollection(Protocol):
    """Protocol for CanonicalSymbolCollection containers."""
    @property
    def repository_id(self) -> str: ...
    @property
    def symbols(self) -> List[ICanonicalSymbol]: ...
    def get_symbol(self, id: SymbolID) -> Optional[ICanonicalSymbol]: ...
    def get_by_fqn(self, fqn: str) -> Optional[ICanonicalSymbol]: ...
    def get_symbols_in_namespace(self, namespace_id: NamespaceID) -> List[ICanonicalSymbol]: ...


@runtime_checkable
class ISymbolIdentityBuilderFacade(Protocol):
    """Protocol for Symbol Identity Builder Facade."""
    def build_canonical_symbols(
        self,
        raw_collection: RawSymbolCollection,
        tree: NamespaceTree
    ) -> ICanonicalSymbolCollection: ...
