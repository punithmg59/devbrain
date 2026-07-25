"""
core/symbol_table/builder.py
-----------------------------
SymbolTableBuilder Facade Engine for assembling multi-dimensional SymbolTable indexes.
"""

from __future__ import annotations

import time
from typing import Dict, List

from core.namespaces.tree import NamespaceTree
from core.symbol_identity import CanonicalSymbol, CanonicalSymbolCollection
from core.symbol_table.diagnostics import SymbolTableDiagnostics
from core.symbol_table.indexes import SymbolIndexSet
from core.symbol_table.models import SymbolTable, SymbolTableStatistics
from core.symbol_table.validator import SymbolTableValidator
from core.symbols import Language, SymbolID, SymbolKind, VisibilityKind
from core.symbols.ids import NamespaceID


class SymbolTableBuilder:
    """
    Facade engine that converts CanonicalSymbolCollection and NamespaceTree into an immutable SymbolTable.
    """

    def build_symbol_table(
        self,
        collection: CanonicalSymbolCollection,
        tree: NamespaceTree
    ) -> SymbolTable:
        """
        Main Facade Entrypoint.
        """
        start_time = time.perf_counter()
        repository_id = collection.repository_id
        diagnostics = SymbolTableDiagnostics()

        by_id: Dict[SymbolID, CanonicalSymbol] = {}
        by_fqn: Dict[str, CanonicalSymbol] = {}
        by_name: Dict[str, List[CanonicalSymbol]] = {}
        by_namespace: Dict[NamespaceID, List[CanonicalSymbol]] = {}
        by_repository: Dict[str, List[CanonicalSymbol]] = {}
        by_file: Dict[str, List[CanonicalSymbol]] = {}
        by_language: Dict[Language, List[CanonicalSymbol]] = {}
        by_kind: Dict[SymbolKind, List[CanonicalSymbol]] = {}
        by_visibility: Dict[VisibilityKind, List[CanonicalSymbol]] = {}
        by_parent_ns: Dict[NamespaceID, List[CanonicalSymbol]] = {}
        by_child_ns: Dict[NamespaceID, List[CanonicalSymbol]] = {}

        unique_files: set[str] = set()
        unique_namespaces: set[NamespaceID] = set()

        for sym in collection.symbols:
            try:
                # 1. O(1) Primary Indexes
                by_id[sym.id] = sym
                fqn_str = sym.fqn.to_string()
                by_fqn[fqn_str] = sym

                # 2. Secondary Grouping Indexes
                by_name.setdefault(sym.name, []).append(sym)
                by_namespace.setdefault(sym.namespace_id, []).append(sym)
                by_repository.setdefault(sym.repository_id, []).append(sym)
                by_file.setdefault(sym.file_path, []).append(sym)
                by_language.setdefault(sym.language, []).append(sym)
                by_kind.setdefault(sym.kind, []).append(sym)
                by_visibility.setdefault(sym.visibility.kind, []).append(sym)

                unique_files.add(sym.file_path)
                unique_namespaces.add(sym.namespace_id)

                # Parent and child namespace mapping integration
                ns_node = tree.get_node(sym.namespace_id)
                if ns_node and ns_node.parent_id:
                    by_parent_ns.setdefault(ns_node.parent_id, []).append(sym)
                by_child_ns.setdefault(sym.namespace_id, []).append(sym)

            except Exception as e:
                diagnostics = diagnostics.add_error(
                    message=f"Error indexing symbol '{sym.name}': {str(e)}",
                    file_path=sym.file_path,
                    code="ERR_SYMBOL_INDEXING_FAILED"
                )

        indexes = SymbolIndexSet(
            by_id=by_id,
            by_fqn=by_fqn,
            by_name=by_name,
            by_namespace=by_namespace,
            by_repository=by_repository,
            by_file=by_file,
            by_language=by_language,
            by_kind=by_kind,
            by_visibility=by_visibility,
            by_parent_namespace=by_parent_ns,
            by_child_namespace=by_child_ns
        )

        # Integrity & Coverage Validation
        val_diags = SymbolTableValidator.validate(collection.symbols, indexes, tree, repository_id)
        if val_diags.diagnostics:
            all_diags = diagnostics.diagnostics + val_diags.diagnostics
            diagnostics = SymbolTableDiagnostics(diagnostics=all_diags)

        duration_ms = (time.perf_counter() - start_time) * 1000.0

        stats = SymbolTableStatistics(
            total_symbols=len(by_id),
            total_indexed_fqns=len(by_fqn),
            total_files=len(unique_files),
            total_namespaces=len(unique_namespaces),
            duration_ms=duration_ms
        )

        return SymbolTable(
            repository_id=repository_id,
            indexes=indexes,
            statistics=stats,
            diagnostics=diagnostics
        )
