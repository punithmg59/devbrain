"""
analysis/import_resolution/import_resolver.py
---------------------------------------------
Phase 4.6 — Import Resolution Coordinator.

Main entry point that coordinates `ModuleIndex`, `ImportLinker`, and `ImportValidator`
to resolve cross-file import statements across a repository.

Design Principles
-----------------
- **Clean Architecture Pipeline**: Coordinates module indexing, symbol linking, and telemetry.
- **Robust Classification**: Classifies imports into Internal, Standard Library, or External.
"""

from __future__ import annotations

import os
import time
from typing import Any, Dict, List, Optional, Tuple

from models.import_models import (
    ImportAlias,
    ImportKind,
    ImportMetrics,
    ImportRecord,
    ImportResolution,
    ImportResolutionResult,
    ImportResolutionStatus,
)
from models.semantic import ExtractedImport, ExtractedModule, SemanticExtractionResult
from analysis.symbol_table.symbol_table import SymbolTable
from analysis.import_resolution.import_index import ImportIndex
from analysis.import_resolution.import_linker import ImportLinker
from analysis.import_resolution.import_validator import ImportValidator
from analysis.import_resolution.module_index import ModuleIndex
from utils.logger import get_logger

logger = get_logger(__name__)


class ImportResolver:
    """
    Coordinator engine for performing repository import resolution.

    Usage::

        resolver = ImportResolver(repository_id="repo1")
        result = resolver.resolve_results([sem_result1, sem_result2], symbol_table)
    """

    def __init__(self, repository_id: str = "repo") -> None:
        self.repository_id = repository_id
        self._linker = ImportLinker()
        self._validator = ImportValidator()

    def resolve_result(
        self,
        extraction_result: SemanticExtractionResult,
        symbol_table: SymbolTable,
    ) -> ImportResolutionResult:
        """Resolve imports for a single `SemanticExtractionResult`."""
        return self.resolve_results([extraction_result], symbol_table)

    def resolve_results(
        self,
        extraction_results: List[SemanticExtractionResult],
        symbol_table: SymbolTable,
    ) -> ImportResolutionResult:
        """
        Resolve import statements across multiple `SemanticExtractionResult` objects.

        Parameters
        ----------
        extraction_results:
            List of `SemanticExtractionResult` objects.
        symbol_table:
            Repository `SymbolTable`.

        Returns
        -------
        ImportResolutionResult
        """
        start_time = time.perf_counter()

        # 1. Build Repository Module Index
        module_index = ModuleIndex()
        for res in extraction_results:
            module_index.register_file(res.file_path, res.module.name)

        # Also register files present in SymbolTable
        for sym in symbol_table.symbols.values():
            if sym.kind == "module" and sym.file_path:
                module_index.register_file(sym.file_path, sym.fqn)

        # 2. Extract ImportRecords & Resolve Each Import
        import_index = ImportIndex()
        metrics = ImportMetrics()

        for res in extraction_results:
            source_file = res.file_path
            source_module_fqn = res.module.name or module_index.path_to_fqn(source_file)

            for imp in res.module.imports:
                records = self._convert_extracted_import(imp, source_file, source_module_fqn)
                for rec in records:
                    resolution = self._resolve_single_import(rec, module_index, symbol_table)
                    import_index.add_import(rec, resolution)

                    # Update Metrics
                    metrics.total_imports += 1
                    if rec.is_relative:
                        metrics.relative_count += 1
                    if rec.alias:
                        metrics.alias_count += 1
                    if rec.is_wildcard:
                        metrics.wildcard_count += 1

                    if resolution.status == ImportResolutionStatus.RESOLVED_INTERNAL:
                        metrics.resolved_internal += 1
                    elif resolution.status == ImportResolutionStatus.RESOLVED_STDLIB:
                        metrics.resolved_stdlib += 1
                    elif resolution.status == ImportResolutionStatus.RESOLVED_EXTERNAL:
                        metrics.resolved_external += 1
                    else:
                        metrics.unresolved_count += 1

        # 3. Validate Import Graph Integrity
        val_report = self._validator.validate(import_index, module_index, symbol_table)
        warnings = [i.message for i in val_report.issues if i.severity == "warning"]
        errors = [i.message for i in val_report.issues if i.severity == "error"]

        duration_ms = (time.perf_counter() - start_time) * 1000.0
        metrics.build_duration_ms = round(duration_ms, 3)
        metrics.memory_bytes = self._get_memory_bytes()

        return ImportResolutionResult(
            repository_id=self.repository_id,
            resolutions=import_index.resolutions,
            imports=import_index.imports,
            metrics=metrics,
            warnings=warnings,
            errors=errors,
        )

    # ------------------------------------------------------------------
    # Internal Helpers
    # ------------------------------------------------------------------

    def _convert_extracted_import(
        self,
        imp: ExtractedImport,
        source_file: str,
        source_module_fqn: str,
    ) -> List[ImportRecord]:
        """Convert a single `ExtractedImport` into one or more `ImportRecord` items."""
        records: List[ImportRecord] = []

        is_relative = imp.is_relative or imp.relative_level > 0

        # Case A: plain module import (e.g. `import os`, `import numpy as np`)
        if not imp.imported_names:
            alias = imp.aliases[0] if imp.aliases else None
            kind = ImportKind.ALIAS if alias else (ImportKind.RELATIVE if is_relative else ImportKind.MODULE)

            records.append(
                ImportRecord(
                    kind=kind,
                    statement_snippet=imp.module,
                    source_file_path=source_file,
                    source_module_fqn=source_module_fqn,
                    imported_module_name=imp.module,
                    imported_symbol_name=None,
                    alias=alias,
                    relative_level=imp.relative_level,
                    range=imp.range,
                    is_relative=is_relative,
                    is_wildcard=False,
                )
            )

        # Case B: from-import (e.g. `from app.auth import AuthService, User as U`, `from models import *`)
        else:
            for idx, name in enumerate(imp.imported_names):
                alias = imp.aliases[idx] if idx < len(imp.aliases) else None
                is_wildcard = name == "*"

                if is_wildcard:
                    kind = ImportKind.WILDCARD
                elif alias:
                    kind = ImportKind.FROM_IMPORT_ALIAS
                elif is_relative:
                    kind = ImportKind.RELATIVE
                else:
                    kind = ImportKind.FROM_IMPORT

                snippet = f"from {imp.module} import {name}" + (f" as {alias}" if alias else "")

                records.append(
                    ImportRecord(
                        kind=kind,
                        statement_snippet=snippet,
                        source_file_path=source_file,
                        source_module_fqn=source_module_fqn,
                        imported_module_name=imp.module,
                        imported_symbol_name=None if is_wildcard else name,
                        alias=alias,
                        relative_level=imp.relative_level,
                        range=imp.range,
                        is_relative=is_relative,
                        is_wildcard=is_wildcard,
                    )
                )

        return records

    def _resolve_single_import(
        self,
        rec: ImportRecord,
        module_index: ModuleIndex,
        symbol_table: SymbolTable,
    ) -> ImportResolution:
        """Resolve a single `ImportRecord` against `ModuleIndex` and `SymbolTable`."""
        # 1. Handle Relative Module Computation
        if rec.is_relative:
            target_module_fqn = module_index.resolve_relative_import(
                rec.source_module_fqn,
                rec.relative_level,
                rec.imported_module_name if rec.imported_module_name != "." else None,
            )
        else:
            target_module_fqn = rec.imported_module_name

        # 2. Check Standard Library Module
        if not rec.is_relative and module_index.is_stdlib_module(target_module_fqn):
            return ImportResolution(
                import_id=rec.id,
                status=ImportResolutionStatus.RESOLVED_STDLIB,
                target_module_fqn=target_module_fqn,
                is_stdlib=True,
                is_external=False,
            )

        # 3. Check Internal Repository Module
        target_file_path = module_index.get_file_path(target_module_fqn) if target_module_fqn else None

        if target_file_path or (target_module_fqn and module_index.is_registered_module(target_module_fqn)):
            # Case 3a: Wildcard import
            if rec.is_wildcard:
                exported_syms = self._linker.expand_wildcard_symbols(target_module_fqn, symbol_table)
                return ImportResolution(
                    import_id=rec.id,
                    status=ImportResolutionStatus.RESOLVED_INTERNAL,
                    target_module_fqn=target_module_fqn,
                    target_file_path=target_file_path,
                    wildcard_symbol_ids=[s.id for s in exported_syms],
                )

            # Case 3b: From-import symbol (e.g. AuthService)
            if rec.imported_symbol_name:
                sym = self._linker.link_symbol(target_module_fqn, rec.imported_symbol_name, symbol_table)
                if sym:
                    return ImportResolution(
                        import_id=rec.id,
                        status=ImportResolutionStatus.RESOLVED_INTERNAL,
                        target_module_fqn=target_module_fqn,
                        target_file_path=target_file_path,
                        target_symbol_id=sym.id,
                        target_symbol_fqn=sym.fqn,
                    )
                else:
                    # Target module found, but symbol missing
                    return ImportResolution(
                        import_id=rec.id,
                        status=ImportResolutionStatus.UNRESOLVED_SYMBOL,
                        target_module_fqn=target_module_fqn,
                        target_file_path=target_file_path,
                        error_message=f"Symbol '{rec.imported_symbol_name}' not found in module '{target_module_fqn}'",
                    )

            # Case 3c: Plain module import (e.g. import app.auth)
            return ImportResolution(
                import_id=rec.id,
                status=ImportResolutionStatus.RESOLVED_INTERNAL,
                target_module_fqn=target_module_fqn,
                target_file_path=target_file_path,
            )

        # 4. Fallback: Third-party External Library (e.g. requests, fastapi, numpy)
        if not rec.is_relative:
            return ImportResolution(
                import_id=rec.id,
                status=ImportResolutionStatus.RESOLVED_EXTERNAL,
                target_module_fqn=target_module_fqn,
                is_stdlib=False,
                is_external=True,
            )

        # 5. Unresolved Relative Import
        return ImportResolution(
            import_id=rec.id,
            status=ImportResolutionStatus.UNRESOLVED_MODULE,
            target_module_fqn=target_module_fqn,
            error_message=f"Relative module '{target_module_fqn}' could not be resolved in repository",
        )

    @staticmethod
    def _get_memory_bytes() -> int:
        try:
            import psutil
            return psutil.Process(os.getpid()).memory_info().rss
        except Exception:
            return 0
