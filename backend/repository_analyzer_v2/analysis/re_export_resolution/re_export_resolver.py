"""
analysis/re_export_resolution/re_export_resolver.py
----------------------------------------------------
Phase 4.7.1 — Recursive Re-Export Symbol Resolver.

Resolves an (package_fqn, exported_name) pair through potentially multi-level
re-export chains to the ultimate defining Symbol in the SymbolTable.

Resolution Strategy
-------------------
1. O(1) ExportIndex named-lookup → ExportRecord
2. If ExportRecord.source_module_fqn known:
   a. Search SymbolTable for `source_module_fqn.original_name` directly
   b. If not found recursively try source_module_fqn as another package with
      sub-exports (recursive call with depth guard)
3. Star exports: iterate all star ExportRecord.source_module_fqn entries,
   search each for the symbol
4. __all__ exports: source_module_fqn is unknown; search the full SymbolTable
   for any symbol in the package matching the name

Cycle Protection
----------------
visited: Set[Tuple[str, str]] carries (pkg_fqn, name) pairs seen in the
current resolution path. Depth is also capped at MAX_CHAIN_DEPTH = 10.

Design Principles
-----------------
- **Non-Throwing**: Returns None on failure; never raises.
- **Cycle-Safe**: Visited-set prevents infinite loops on circular re-exports.
- **Performance**: Each recursive call is O(1) for named lookups.
"""

from __future__ import annotations

from typing import Optional, Set, Tuple

from models.re_export_models import ExportRecord, ExportType
from models.symbol import Symbol, SymbolKind
from analysis.symbol_table.symbol_table import SymbolTable
from analysis.re_export_resolution.re_export_index import ReExportIndex
from utils.logger import get_logger

logger = get_logger(__name__)

MAX_CHAIN_DEPTH = 10


class ReExportResolver:
    """
    Recursive resolver that follows re-export chains to locate the ultimate
    defining Symbol for a (package_fqn, exported_name) pair.

    Usage::

        resolver = ReExportResolver()
        sym, fqn = resolver.resolve("fastapi", "FastAPI", export_index, symbol_table)
    """

    def resolve(
        self,
        package_fqn: str,
        exported_name: str,
        export_index: ReExportIndex,
        symbol_table: SymbolTable,
        visited: Optional[Set[Tuple[str, str]]] = None,
        depth: int = 0,
    ) -> Tuple[Optional[Symbol], Optional[str]]:
        """
        Resolve exported_name exported from package_fqn to a (Symbol, fqn) pair.

        Parameters
        ----------
        package_fqn:
            Package FQN declaring the re-export (e.g. 'fastapi').
        exported_name:
            Name as seen by the importer (e.g. 'FastAPI').
        export_index:
            Pre-built ReExportIndex.
        symbol_table:
            Repository SymbolTable.
        visited:
            Set of (pkg_fqn, name) pairs visited in the current chain; prevents cycles.
        depth:
            Current recursion depth.

        Returns
        -------
        Tuple[Optional[Symbol], Optional[str]]
            (Symbol, target_fqn) if found, (None, None) if not.
        """
        if visited is None:
            visited = set()

        chain_key = (package_fqn, exported_name)
        if chain_key in visited or depth > MAX_CHAIN_DEPTH:
            logger.debug(
                "Re-export resolver: cycle or depth limit at %s.%s (depth=%d)",
                package_fqn,
                exported_name,
                depth,
            )
            return None, None

        visited = visited | {chain_key}  # immutable copy for safety

        # --- Strategy 1: Named lookup in ExportIndex ---
        rec = export_index.lookup(package_fqn, exported_name)
        if rec:
            return self._resolve_from_record(
                rec, exported_name, export_index, symbol_table, visited, depth
            )

        # --- Strategy 2: Star export expansion ---
        star_exports = export_index.get_star_exports(package_fqn)
        for star_rec in star_exports:
            if star_rec.source_module_fqn:
                sym, fqn = self._search_symbol_in_module(
                    star_rec.source_module_fqn, exported_name, symbol_table
                )
                if sym:
                    return sym, fqn

                # Recurse into star source as a package too
                sym, fqn = self.resolve(
                    star_rec.source_module_fqn,
                    exported_name,
                    export_index,
                    symbol_table,
                    visited,
                    depth + 1,
                )
                if sym:
                    return sym, fqn

        return None, None

    # ------------------------------------------------------------------
    # Internal Helpers
    # ------------------------------------------------------------------

    def _resolve_from_record(
        self,
        rec: ExportRecord,
        exported_name: str,
        export_index: ReExportIndex,
        symbol_table: SymbolTable,
        visited: Set[Tuple[str, str]],
        depth: int,
    ) -> Tuple[Optional[Symbol], Optional[str]]:
        """Resolve an ExportRecord to its target Symbol."""
        # If the source module is known, search there first
        if rec.source_module_fqn:
            sym, fqn = self._search_symbol_in_module(
                rec.source_module_fqn, rec.original_name, symbol_table
            )
            if sym:
                return sym, fqn

            # Symbol not directly in source module → maybe source is also a package
            # (recursive chain: fastapi → applications → ... → FastAPI)
            sym, fqn = self.resolve(
                rec.source_module_fqn,
                rec.original_name,
                export_index,
                symbol_table,
                visited,
                depth + 1,
            )
            if sym:
                return sym, fqn

        # __all__-based records with no source_module_fqn: scan full package namespace
        sym, fqn = self._search_symbol_in_package(
            rec.package_fqn, rec.original_name, symbol_table
        )
        return sym, fqn

    @staticmethod
    def _search_symbol_in_module(
        module_fqn: str,
        symbol_name: str,
        symbol_table: SymbolTable,
    ) -> Tuple[Optional[Symbol], Optional[str]]:
        """
        Search the SymbolTable for `module_fqn.symbol_name`.

        Tries exact FQN first, then file-path match for symbols in that module.
        """
        # 1. Exact FQN match
        expected_fqn = f"{module_fqn}.{symbol_name}"
        for sym in symbol_table.symbols.values():
            if sym.fqn == expected_fqn and sym.kind != SymbolKind.MODULE:
                return sym, sym.fqn

        # 2. Find module symbol, then search by name within its file
        module_sym: Optional[Symbol] = None
        for sym in symbol_table.symbols.values():
            if sym.fqn == module_fqn and sym.kind == SymbolKind.MODULE:
                module_sym = sym
                break

        if module_sym and module_sym.file_path:
            for sym in symbol_table.symbols.values():
                if (
                    sym.file_path == module_sym.file_path
                    and sym.name == symbol_name
                    and sym.kind != SymbolKind.MODULE
                ):
                    return sym, sym.fqn

        return None, None

    @staticmethod
    def _search_symbol_in_package(
        package_fqn: str,
        symbol_name: str,
        symbol_table: SymbolTable,
    ) -> Tuple[Optional[Symbol], Optional[str]]:
        """
        Broad search for `symbol_name` anywhere within `package_fqn` subtree.

        Used when __all__ exports don't carry source_module_fqn.
        """
        prefix = package_fqn + "."
        for sym in symbol_table.symbols.values():
            if (
                sym.name == symbol_name
                and sym.kind != SymbolKind.MODULE
                and (sym.fqn == f"{package_fqn}.{symbol_name}" or sym.fqn.startswith(prefix))
            ):
                return sym, sym.fqn
        return None, None
