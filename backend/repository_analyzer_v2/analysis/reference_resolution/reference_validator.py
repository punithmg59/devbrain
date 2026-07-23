"""
analysis/reference_resolution/reference_validator.py
----------------------------------------------------
Phase 4.7 — Reference Resolution Validator.

Validates reference binding integrity, checking for unresolved references, dangling
symbol IDs, invalid scope IDs, and missing source locations.

Design Principles
-----------------
- **Structured Validation Report**: Returns `ReferenceValidationReport` with issue breakdowns.
- **Non-Throwing**: Records issues as errors and warnings without raising exceptions.
"""

from __future__ import annotations

from typing import List, Set

from models.reference_models import (
    ReferenceValidationIssue,
    ReferenceValidationReport,
)
from analysis.scope_resolution.scope_tree import ScopeTree
from analysis.symbol_table.symbol_table import SymbolTable
from analysis.reference_resolution.reference_index import ReferenceIndex


class ReferenceValidator:
    """
    Validator engine for checking graph integrity of reference bindings.

    Usage::

        validator = ReferenceValidator()
        report = validator.validate(ref_index, symbol_table, scope_tree)
        assert report.is_valid
    """

    def validate(
        self,
        ref_index: ReferenceIndex,
        symbol_table: SymbolTable,
        scope_tree: ScopeTree,
    ) -> ReferenceValidationReport:
        """
        Validate binding integrity of references.

        Parameters
        ----------
        ref_index:
            Pre-indexed reference records.
        symbol_table:
            Repository `SymbolTable`.
        scope_tree:
            Lexical `ScopeTree`.

        Returns
        -------
        ReferenceValidationReport
        """
        issues: List[ReferenceValidationIssue] = []
        error_count = 0
        warning_count = 0

        all_symbol_ids: Set[str] = set(symbol_table.symbols.keys())

        for ref_id, rec in ref_index.references.items():
            res = ref_index.resolutions.get(ref_id)

            # 1. Unresolved Reference Warning
            if not res or not res.is_resolved or not rec.symbol_id:
                issues.append(
                    ReferenceValidationIssue(
                        severity="warning",
                        code="UNRESOLVED_REFERENCE",
                        message=f"Unresolved reference to '{rec.symbol_name}' in '{rec.file_path}' (line {rec.line})",
                        reference_id=rec.id,
                        file_path=rec.file_path,
                    )
                )
                warning_count += 1

            # 2. Dangling Symbol ID Error
            elif rec.symbol_id and rec.symbol_id not in all_symbol_ids:
                issues.append(
                    ReferenceValidationIssue(
                        severity="error",
                        code="DANGLING_SYMBOL_ID",
                        message=f"Reference '{rec.symbol_name}' references symbol ID '{rec.symbol_id}' which does not exist in SymbolTable",
                        reference_id=rec.id,
                        file_path=rec.file_path,
                    )
                )
                error_count += 1

            # 3. Invalid Scope ID Warning
            if rec.scope_id and rec.scope_id != "root" and rec.scope_id not in scope_tree.scopes:
                issues.append(
                    ReferenceValidationIssue(
                        severity="warning",
                        code="INVALID_SCOPE",
                        message=f"Reference '{rec.symbol_name}' references scope ID '{rec.scope_id}' which does not exist in ScopeTree",
                        reference_id=rec.id,
                        file_path=rec.file_path,
                    )
                )
                warning_count += 1

            # 4. Missing Location Bounds
            if rec.line <= 0 or rec.end_line < rec.line:
                issues.append(
                    ReferenceValidationIssue(
                        severity="warning",
                        code="MISSING_LOCATION",
                        message=f"Reference '{rec.symbol_name}' has invalid source line bounds ({rec.line}..{rec.end_line})",
                        reference_id=rec.id,
                        file_path=rec.file_path,
                    )
                )
                warning_count += 1

        is_valid = error_count == 0

        return ReferenceValidationReport(
            is_valid=is_valid,
            issues=issues,
            error_count=error_count,
            warning_count=warning_count,
        )
