"""
analysis/symbol_table/symbol_validator.py
-----------------------------------------
Phase 4.4 — Symbol Table Integrity Validator.

Performs static validation over a `SymbolTable` to detect duplicate IDs, duplicate FQNs,
dangling parent IDs, circular parent hierarchies, and invalid source location ranges.

Design Principles
-----------------
- **Structured Validation Report**: Returns `SymbolValidationReport` with categorized issues.
- **Non-Throwing**: Returns report containing errors and warnings rather than raising runtime exceptions.
- **Language Agnostic**: Validates pure symbol graph contracts.
"""

from __future__ import annotations

from typing import Dict, List, Set

from models.symbol import (
    Symbol,
    SymbolValidationIssue,
    SymbolValidationReport,
)
from analysis.symbol_table.symbol_table import SymbolTable


class SymbolTableValidator:
    """
    Validator engine for checking the internal structural integrity of a `SymbolTable`.

    Usage::

        validator = SymbolTableValidator()
        report = validator.validate(symbol_table)
        assert report.is_valid
    """

    def validate(self, symbol_table: SymbolTable) -> SymbolValidationReport:
        """
        Validate structural integrity of a `SymbolTable`.

        Parameters
        ----------
        symbol_table:
            The `SymbolTable` to validate.

        Returns
        -------
        SymbolValidationReport
            Report containing errors, warnings, and issue breakdowns.
        """
        issues: List[SymbolValidationIssue] = []
        error_count = 0
        warning_count = 0

        fqn_map: Dict[str, List[Symbol]] = {}
        all_ids: Set[str] = set(symbol_table.symbols.keys())

        for sym in symbol_table.symbols.values():
            # 1. Missing Name
            if not sym.name or not sym.name.strip():
                issues.append(
                    SymbolValidationIssue(
                        severity="error",
                        code="MISSING_NAME",
                        message=f"Symbol '{sym.id}' has an empty or missing name",
                        symbol_id=sym.id,
                        fqn=sym.fqn,
                    )
                )
                error_count += 1

            # 2. Duplicate FQNs
            if sym.fqn in fqn_map:
                fqn_map[sym.fqn].append(sym)
            else:
                fqn_map[sym.fqn] = [sym]

            # 3. Dangling Parent ID
            if sym.parent_id and sym.parent_id not in all_ids:
                issues.append(
                    SymbolValidationIssue(
                        severity="error",
                        code="DANGLING_PARENT",
                        message=f"Symbol '{sym.fqn}' ({sym.id}) references parent ID '{sym.parent_id}' which does not exist in table",
                        symbol_id=sym.id,
                        fqn=sym.fqn,
                    )
                )
                error_count += 1

            # 4. Invalid Source Location Range
            if sym.location and sym.location.range:
                rng = sym.location.range
                if rng.start.line > rng.end.line or (
                    rng.start.line == rng.end.line and rng.start.column > rng.end.column
                ):
                    issues.append(
                        SymbolValidationIssue(
                            severity="warning",
                            code="INVALID_LOCATION",
                            message=f"Symbol '{sym.fqn}' has inverted start/end source range",
                            symbol_id=sym.id,
                            fqn=sym.fqn,
                        )
                    )
                    warning_count += 1

        # Check duplicate FQNs
        for fqn, sym_list in fqn_map.items():
            if len(sym_list) > 1:
                issues.append(
                    SymbolValidationIssue(
                        severity="warning",
                        code="DUPLICATE_FQN",
                        message=f"Duplicate FQN '{fqn}' shared by {len(sym_list)} symbols",
                        fqn=fqn,
                    )
                )
                warning_count += 1

        # 5. Circular Parent Reference Chains
        for sym_id, sym in symbol_table.symbols.items():
            visited: Set[str] = {sym_id}
            curr = sym
            while curr.parent_id:
                pid = curr.parent_id
                if pid in visited:
                    issues.append(
                        SymbolValidationIssue(
                            severity="error",
                            code="CIRCULAR_PARENT",
                            message=f"Circular parent reference chain detected involving symbol '{sym.fqn}' ({sym_id}) and parent '{pid}'",
                            symbol_id=sym_id,
                            fqn=sym.fqn,
                        )
                    )
                    error_count += 1
                    break
                visited.add(pid)
                curr = symbol_table.symbols.get(pid)  # type: ignore
                if not curr:
                    break

        is_valid = error_count == 0

        return SymbolValidationReport(
            is_valid=is_valid,
            issues=issues,
            error_count=error_count,
            warning_count=warning_count,
        )
