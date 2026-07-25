"""
core/symbol_table/validator.py
-------------------------------
Index Coverage and Consistency Validator for SymbolTable.
"""

from __future__ import annotations

from typing import Set

from core.namespaces.tree import NamespaceTree
from core.symbol_identity import CanonicalSymbol
from core.symbol_table.diagnostics import SymbolTableDiagnostics
from core.symbols import SymbolID


class SymbolTableValidator:
    """
    Validates complete multi-index coverage and consistency for SymbolTable.
    """

    @classmethod
    def validate(
        cls,
        table_symbols: list[CanonicalSymbol],
        indexes: Any,
        tree: NamespaceTree,
        repository_id: str
    ) -> SymbolTableDiagnostics:
        diagnostics = SymbolTableDiagnostics()
        all_ids: Set[SymbolID] = {sym.id for sym in table_symbols}

        # 1. Verify every symbol is present in by_id and by_fqn
        for sym in table_symbols:
            if sym.id not in indexes.by_id:
                diagnostics = diagnostics.add_error(
                    message=f"Symbol '{sym.name}' ({sym.id}) missing from by_id index.",
                    file_path=sym.file_path,
                    code="ERR_MISSING_ID_INDEX"
                )

            fqn_str = sym.fqn.to_string()
            if fqn_str not in indexes.by_fqn:
                diagnostics = diagnostics.add_error(
                    message=f"Symbol '{sym.name}' ({sym.fqn}) missing from by_fqn index.",
                    file_path=sym.file_path,
                    code="ERR_MISSING_FQN_INDEX"
                )

            # Check namespace tree reference
            if not tree.get_node(sym.namespace_id):
                diagnostics = diagnostics.add_warning(
                    message=f"Symbol '{sym.name}' ({sym.id}) references unindexed NamespaceID '{sym.namespace_id}'.",
                    file_path=sym.file_path,
                    code="WARN_UNINDEXED_NAMESPACE"
                )

        # 2. Check for dangling entries in indexes
        for sid in indexes.by_id:
            if sid not in all_ids:
                diagnostics = diagnostics.add_error(
                    message=f"SymbolID '{sid}' present in index but missing from canonical symbols list.",
                    code="ERR_DANGLING_INDEX_ENTRY"
                )

        return diagnostics
