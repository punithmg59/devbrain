"""
core/symbol_identity/validator.py
----------------------------------
Integrity and Duplicate Validator for CanonicalSymbolCollection.
"""

from __future__ import annotations

from typing import Set

from core.namespaces.tree import NamespaceTree
from core.symbol_identity.diagnostics import IdentityDiagnostics
from core.symbol_identity.models import CanonicalSymbol
from core.symbols import SymbolID


class SymbolIdentityValidator:
    """
    Validates identity uniqueness and namespace integrity of CanonicalSymbol objects.
    """

    @classmethod
    def validate(
        cls,
        symbols: list[CanonicalSymbol],
        tree: NamespaceTree,
        repository_id: str
    ) -> IdentityDiagnostics:
        diagnostics = IdentityDiagnostics()
        seen_symbol_ids: Set[SymbolID] = set()
        seen_fqns: Set[str] = set()

        for sym in symbols:
            # 1. Check SymbolID uniqueness
            if sym.id in seen_symbol_ids:
                diagnostics = diagnostics.add_error(
                    message=f"Duplicate SymbolID '{sym.id}' detected for symbol '{sym.fqn}'.",
                    file_path=sym.file_path,
                    code="ERR_DUPLICATE_SYMBOL_ID"
                )
            seen_symbol_ids.add(sym.id)

            # 2. Check FQN collision / overload warning
            fqn_str = sym.fqn.to_string()
            if fqn_str in seen_fqns:
                diagnostics = diagnostics.add_warning(
                    message=f"Multiple declarations share QualifiedName '{fqn_str}'. Overload or duplicate declaration.",
                    file_path=sym.file_path,
                    code="WARN_DUPLICATE_FQN"
                )
            seen_fqns.add(fqn_str)

            # 3. Check namespace presence
            ns_node = tree.get_node(sym.namespace_id)
            if not ns_node:
                diagnostics = diagnostics.add_error(
                    message=f"CanonicalSymbol '{sym.name}' references non-existent NamespaceID '{sym.namespace_id}'.",
                    file_path=sym.file_path,
                    code="ERR_MISSING_NAMESPACE"
                )

        return diagnostics
