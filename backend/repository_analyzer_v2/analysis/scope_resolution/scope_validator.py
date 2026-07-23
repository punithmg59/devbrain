"""
analysis/scope_resolution/scope_validator.py
---------------------------------------------
Phase 4.5 — Scope Integrity Validator.

Validates structural integrity of a `ScopeTree`, checking for dangling parents,
circular scope chains, orphan scopes, and unowned symbol IDs.

Design Principles
-----------------
- **Structured Validation Report**: Returns `ScopeValidationReport` with issue breakdowns.
- **Non-Throwing**: Records issues as errors and warnings without raising exceptions.
"""

from __future__ import annotations

from typing import Dict, List, Set

from models.scope import (
    Scope,
    ScopeValidationIssue,
    ScopeValidationReport,
)
from analysis.symbol_table.symbol_table import SymbolTable
from analysis.scope_resolution.scope_tree import ScopeTree


class ScopeValidator:
    """
    Validator engine for checking graph integrity of a `ScopeTree`.

    Usage::

        validator = ScopeValidator()
        report = validator.validate(scope_tree, symbol_table)
        assert report.is_valid
    """

    def validate(
        self,
        tree: ScopeTree,
        symbol_table: SymbolTable,
    ) -> ScopeValidationReport:
        """
        Validate structural integrity of a `ScopeTree`.

        Parameters
        ----------
        tree:
            The `ScopeTree` to validate.
        symbol_table:
            The repository `SymbolTable`.

        Returns
        -------
        ScopeValidationReport
        """
        issues: List[ScopeValidationIssue] = []
        error_count = 0
        warning_count = 0

        all_scope_ids: Set[str] = set(tree.scopes.keys())

        for scope in tree.scopes.values():
            # 1. Dangling Parent Scope ID
            if scope.parent_id and scope.parent_id not in all_scope_ids:
                issues.append(
                    ScopeValidationIssue(
                        severity="error",
                        code="DANGLING_PARENT",
                        message=f"Scope '{scope.name}' ({scope.id}) references parent scope ID '{scope.parent_id}' which does not exist in tree",
                        scope_id=scope.id,
                    )
                )
                error_count += 1

            # 2. Orphan Scope
            if scope.parent_id is None and scope.id not in tree.root_scope_ids:
                issues.append(
                    ScopeValidationIssue(
                        severity="warning",
                        code="ORPHAN_SCOPE",
                        message=f"Scope '{scope.name}' ({scope.id}) has no parent but is not listed in root_scope_ids",
                        scope_id=scope.id,
                    )
                )
                warning_count += 1

            # 3. Unowned / Missing Symbols
            for sym_id in scope.defined_symbol_ids:
                if sym_id not in symbol_table.symbols:
                    issues.append(
                        ScopeValidationIssue(
                            severity="error",
                            code="UNOWNED_SYMBOL",
                            message=f"Scope '{scope.name}' ({scope.id}) claims defined symbol ID '{sym_id}' which does not exist in SymbolTable",
                            scope_id=scope.id,
                        )
                    )
                    error_count += 1

            # 4. Invalid Scope Location Range
            if scope.location and scope.location.range:
                rng = scope.location.range
                if rng.start.line > rng.end.line or (
                    rng.start.line == rng.end.line and rng.start.column > rng.end.column
                ):
                    issues.append(
                        ScopeValidationIssue(
                            severity="warning",
                            code="INVALID_LOCATION",
                            message=f"Scope '{scope.name}' has inverted source range bounds",
                            scope_id=scope.id,
                        )
                    )
                    warning_count += 1

        # 5. Circular Parent Scope Chains
        for scope_id, scope in tree.scopes.items():
            visited: Set[str] = {scope_id}
            curr = scope
            while curr.parent_id:
                pid = curr.parent_id
                if pid in visited:
                    issues.append(
                        ScopeValidationIssue(
                            severity="error",
                            code="CIRCULAR_SCOPE",
                            message=f"Circular parent scope chain detected involving scope '{scope.name}' ({scope_id}) and parent '{pid}'",
                            scope_id=scope_id,
                        )
                    )
                    error_count += 1
                    break
                visited.add(pid)
                curr = tree.scopes.get(pid)  # type: ignore
                if not curr:
                    break

        is_valid = error_count == 0

        return ScopeValidationReport(
            is_valid=is_valid,
            issues=issues,
            error_count=error_count,
            warning_count=warning_count,
        )
