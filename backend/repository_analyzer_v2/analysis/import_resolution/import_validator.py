"""
analysis/import_resolution/import_validator.py
-----------------------------------------------
Phase 4.6 — Import Graph Integrity Validator.

Validates cross-file import graph integrity, detecting missing modules, missing symbols,
circular import dependencies, broken relative imports, and duplicate import statements.

Design Principles
-----------------
- **Structured Validation Report**: Returns `ImportValidationReport` with issue breakdowns.
- **Cycle Detection**: Detects circular module dependency loops (A -> B -> A).
- **Non-Throwing**: Records issues as errors and warnings without raising exceptions.
"""

from __future__ import annotations

from typing import Dict, List, Set

from models.import_models import (
    ImportResolutionStatus,
    ImportValidationIssue,
    ImportValidationReport,
)
from analysis.symbol_table.symbol_table import SymbolTable
from analysis.import_resolution.import_index import ImportIndex
from analysis.import_resolution.module_index import ModuleIndex


class ImportValidator:
    """
    Validator engine for checking graph integrity of repository imports.

    Usage::

        validator = ImportValidator()
        report = validator.validate(import_index, module_index, symbol_table)
        assert report.is_valid
    """

    def validate(
        self,
        import_index: ImportIndex,
        module_index: ModuleIndex,
        symbol_table: SymbolTable,
    ) -> ImportValidationReport:
        """
        Validate integrity of repository imports.

        Parameters
        ----------
        import_index:
            Pre-indexed repository import statements and resolutions.
        module_index:
            Repository module index.
        symbol_table:
            Repository `SymbolTable`.

        Returns
        -------
        ImportValidationReport
        """
        issues: List[ImportValidationIssue] = []
        error_count = 0
        warning_count = 0

        # Track seen imports per file for duplicate detection
        seen_imports_per_file: Dict[str, Set[str]] = {}

        # Build module dependency graph for cycle detection
        module_deps: Dict[str, Set[str]] = {}

        for import_id, rec in import_index.imports.items():
            res = import_index.resolutions.get(import_id)

            # 1. Duplicate Import Statements in Same File
            key = f"{rec.imported_module_name}::{rec.imported_symbol_name}::{rec.alias}"
            seen_set = seen_imports_per_file.setdefault(rec.source_file_path, set())
            if key in seen_set:
                issues.append(
                    ImportValidationIssue(
                        severity="warning",
                        code="DUPLICATE_IMPORT",
                        message=f"Duplicate import statement snippet '{rec.statement_snippet}' in '{rec.source_file_path}'",
                        import_id=rec.id,
                        source_file_path=rec.source_file_path,
                    )
                )
                warning_count += 1
            else:
                seen_set.add(key)

            if not res:
                continue

            # 2. Missing Module Error
            if res.status == ImportResolutionStatus.UNRESOLVED_MODULE:
                issues.append(
                    ImportValidationIssue(
                        severity="error",
                        code="MISSING_MODULE",
                        message=res.error_message or f"Unresolved module '{rec.imported_module_name}' in '{rec.source_file_path}'",
                        import_id=rec.id,
                        source_file_path=rec.source_file_path,
                    )
                )
                error_count += 1

            # 3. Missing Symbol Error
            elif res.status == ImportResolutionStatus.UNRESOLVED_SYMBOL:
                issues.append(
                    ImportValidationIssue(
                        severity="error",
                        code="MISSING_SYMBOL",
                        message=res.error_message or f"Unresolved symbol '{rec.imported_symbol_name}' in module '{res.target_module_fqn}'",
                        import_id=rec.id,
                        source_file_path=rec.source_file_path,
                    )
                )
                error_count += 1

            # Build dependency edge for cycle detection
            if res.status == ImportResolutionStatus.RESOLVED_INTERNAL and res.target_module_fqn:
                if rec.source_module_fqn != res.target_module_fqn:
                    module_deps.setdefault(rec.source_module_fqn, set()).add(res.target_module_fqn)

        # 4. Circular Import Dependency Cycle Detection
        visited_global: Set[str] = set()
        rec_stack: Set[str] = set()
        cycle_modules: Set[str] = set()

        def dfs_cycles(mod_fqn: str, path: List[str]) -> None:
            visited_global.add(mod_fqn)
            rec_stack.add(mod_fqn)
            path.append(mod_fqn)

            for target in module_deps.get(mod_fqn, []):
                if target not in visited_global:
                    dfs_cycles(target, path)
                elif target in rec_stack:
                    # Found a cycle!
                    cycle_start = path.index(target)
                    cycle_chain = " -> ".join(path[cycle_start:] + [target])
                    if target not in cycle_modules:
                        cycle_modules.add(target)
                        issues.append(
                            ImportValidationIssue(
                                severity="warning",
                                code="CIRCULAR_IMPORT",
                                message=f"Circular import dependency cycle detected: {cycle_chain}",
                            )
                        )
                        nonlocal warning_count
                        warning_count += 1

            path.pop()
            rec_stack.remove(mod_fqn)

        for m_fqn in list(module_deps.keys()):
            if m_fqn not in visited_global:
                dfs_cycles(m_fqn, [])

        is_valid = error_count == 0

        return ImportValidationReport(
            is_valid=is_valid,
            issues=issues,
            error_count=error_count,
            warning_count=warning_count,
        )
