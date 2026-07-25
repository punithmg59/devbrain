"""
core/symbol_extractor/validator.py
----------------------------------
Integrity Validator for RawSymbolCollection.
"""

from __future__ import annotations

from typing import Set

from core.namespaces.tree import NamespaceTree
from core.symbol_extractor.diagnostics import SymbolExtractionDiagnostics
from core.symbol_extractor.models import RawSymbol, TemporaryExtractionID


class SymbolExtractionValidator:
    """
    Validates structural consistency and namespace linkage of RawSymbol objects.
    """

    @classmethod
    def validate(
        cls,
        symbols: list[RawSymbol],
        tree: NamespaceTree,
        repository_id: str
    ) -> SymbolExtractionDiagnostics:
        diagnostics = SymbolExtractionDiagnostics()
        seen_temp_ids: Set[TemporaryExtractionID] = set()

        for sym in symbols:
            # 1. Check TemporaryID uniqueness
            if sym.temp_id in seen_temp_ids:
                diagnostics = diagnostics.add_warning(
                    message=f"Duplicate TemporaryExtractionID '{sym.temp_id}' detected.",
                    file_path=sym.file_path,
                    code="WARN_DUPLICATE_TEMP_ID"
                )
            seen_temp_ids.add(sym.temp_id)

            # 2. Check namespace binding
            ns_node = tree.get_node(sym.namespace_id)
            if not ns_node:
                diagnostics = diagnostics.add_error(
                    message=f"Symbol '{sym.name}' references non-existent NamespaceID '{sym.namespace_id}'.",
                    file_path=sym.file_path,
                    line=sym.source_info.range.start.line if sym.source_info else None,
                    code="ERR_MISSING_NAMESPACE"
                )

            # 3. Check repository match
            if sym.repository_id != repository_id:
                diagnostics = diagnostics.add_error(
                    message=f"Symbol '{sym.name}' repository_id '{sym.repository_id}' mismatch with expected '{repository_id}'.",
                    file_path=sym.file_path,
                    code="ERR_REPO_MISMATCH"
                )

        return diagnostics
