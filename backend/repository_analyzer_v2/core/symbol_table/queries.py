"""
core/symbol_table/queries.py
-----------------------------
Immutable Query API Engine for SymbolTable.
"""

from __future__ import annotations

from typing import Iterator, List, Optional, Union

from core.symbol_identity import CanonicalSymbol
from core.symbols import Language, QualifiedName, SymbolID, SymbolKind, VisibilityKind
from core.symbols.ids import NamespaceID


class SymbolTableQueryEngine:
    """
    Read-only Query Engine for performing high-performance multi-index symbol queries.
    """

    @classmethod
    def get_by_symbol_id(cls, table: Any, id: Union[SymbolID, str]) -> Optional[CanonicalSymbol]:
        sym_id = SymbolID(value=id) if isinstance(id, str) else id
        return table.indexes.by_id.get(sym_id)

    @classmethod
    def get_by_qualified_name(cls, table: Any, fqn: Union[str, QualifiedName]) -> Optional[CanonicalSymbol]:
        fqn_str = fqn.to_string() if isinstance(fqn, QualifiedName) else str(fqn).strip()
        return table.indexes.by_fqn.get(fqn_str)

    @classmethod
    def get_by_name(cls, table: Any, name: str) -> List[CanonicalSymbol]:
        return table.indexes.by_name.get(name.strip(), [])

    @classmethod
    def get_namespace_symbols(cls, table: Any, namespace_id: Union[NamespaceID, str]) -> List[CanonicalSymbol]:
        nid = NamespaceID(value=namespace_id) if isinstance(namespace_id, str) else namespace_id
        return table.indexes.by_namespace.get(nid, [])

    @classmethod
    def get_file_symbols(cls, table: Any, file_path: str) -> List[CanonicalSymbol]:
        return table.indexes.by_file.get(file_path.strip(), [])

    @classmethod
    def get_language_symbols(cls, table: Any, language: Union[Language, str]) -> List[CanonicalSymbol]:
        lang = Language(language.lower()) if isinstance(language, str) else language
        return table.indexes.by_language.get(lang, [])

    @classmethod
    def get_symbols_by_kind(cls, table: Any, kind: Union[SymbolKind, str]) -> List[CanonicalSymbol]:
        skind = SymbolKind(kind.lower()) if isinstance(kind, str) else kind
        return table.indexes.by_kind.get(skind, [])

    @classmethod
    def get_visible_symbols(cls, table: Any, visibility: Union[VisibilityKind, str]) -> List[CanonicalSymbol]:
        vis = VisibilityKind(visibility.lower()) if isinstance(visibility, str) else visibility
        return table.indexes.by_visibility.get(vis, [])

    @classmethod
    def contains(cls, table: Any, key: Union[SymbolID, str, QualifiedName]) -> bool:
        if isinstance(key, SymbolID):
            return key in table.indexes.by_id
        key_str = key.to_string() if isinstance(key, QualifiedName) else str(key)
        if key_str.startswith("sym_"):
            return SymbolID(value=key_str) in table.indexes.by_id
        return key_str in table.indexes.by_fqn

    @classmethod
    def exists(cls, table: Any, fqn: Union[str, QualifiedName]) -> bool:
        fqn_str = fqn.to_string() if isinstance(fqn, QualifiedName) else str(fqn).strip()
        return fqn_str in table.indexes.by_fqn

    @classmethod
    def count(cls, table: Any) -> int:
        return len(table.indexes.by_id)

    @classmethod
    def iterate(cls, table: Any) -> Iterator[CanonicalSymbol]:
        yield from table.indexes.by_id.values()
