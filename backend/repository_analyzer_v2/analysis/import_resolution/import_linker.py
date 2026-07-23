"""
analysis/import_resolution/import_linker.py
-------------------------------------------
Phase 4.6 — Cross-File Symbol Linker.

Binds resolved import statements directly to target `SymbolId` instances in the `SymbolTable`.
Expands wildcard `from module import *` statements against exported module symbols.

Design Principles
-----------------
- **Deterministic Cross-File Binding**: Resolves imported names to exact `Symbol` entities.
- **Wildcard Expansion**: Expands `*` imports into explicit symbol lists.
"""

from __future__ import annotations

from typing import List, Optional

from models.symbol import Symbol, SymbolKind
from analysis.symbol_table.symbol_table import SymbolTable


class ImportLinker:
    """
    Cross-file symbol binder linking import targets to repository `SymbolTable` entries.

    Usage::

        linker = ImportLinker()
        sym = linker.link_symbol("app.auth", "AuthService", symbol_table)
    """

    def link_symbol(
        self,
        target_module_fqn: str,
        symbol_name: str,
        symbol_table: SymbolTable,
    ) -> Optional[Symbol]:
        """
        Link an imported symbol name inside a target module to a `Symbol` in `SymbolTable`.

        Parameters
        ----------
        target_module_fqn:
            Target module FQN (e.g. 'app.auth').
        symbol_name:
            Declared symbol name (e.g. 'AuthService').
        symbol_table:
            Repository `SymbolTable`.

        Returns
        -------
        Optional[Symbol]
            Matching target `Symbol`, or None if not found.
        """
        expected_fqn = f"{target_module_fqn}.{symbol_name}"

        # 1. Search by exact FQN
        for s in symbol_table.symbols.values():
            if s.fqn == expected_fqn:
                return s

        # 2. Search symbols in module file by name
        mod_symbols = [
            s for s in symbol_table.symbols.values()
            if (s.fqn == target_module_fqn or s.name == target_module_fqn.split(".")[-1])
            and s.kind == SymbolKind.MODULE
        ]
        module_file_path = mod_symbols[0].file_path if mod_symbols else None

        if module_file_path:
            for s in symbol_table.symbols.values():
                if s.file_path == module_file_path and s.name == symbol_name and s.kind != SymbolKind.MODULE:
                    return s

        return None

    def expand_wildcard_symbols(
        self,
        target_module_fqn: str,
        symbol_table: SymbolTable,
    ) -> List[Symbol]:
        """
        Expand wildcard `from module import *` into matching top-level module symbols.

        Parameters
        ----------
        target_module_fqn:
            Target module FQN (e.g. 'app.models').
        symbol_table:
            Repository `SymbolTable`.

        Returns
        -------
        List[Symbol]
            List of exported `Symbol` entities inside target module.
        """
        mod_symbols = [
            s for s in symbol_table.symbols.values()
            if s.fqn == target_module_fqn and s.kind == SymbolKind.MODULE
        ]
        if not mod_symbols:
            return []

        mod_sym_id = mod_symbols[0].id
        exported: List[Symbol] = []

        for sym in symbol_table.symbols.values():
            if sym.parent_id == mod_sym_id and sym.kind != SymbolKind.MODULE:
                if not sym.name.startswith("_"):
                    exported.append(sym)

        return exported
