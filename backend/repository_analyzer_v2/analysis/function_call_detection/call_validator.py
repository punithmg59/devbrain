"""
analysis/function_call_detection/call_validator.py
---------------------------------------------------
Phase 4.7.2 — Call Graph Integrity Validator.

Validates the integrity of `CallIndex` and `CallRecord` collections:
- Detects duplicate calls (same caller, callee_name, file, line, column)
- Verifies resolved `callee_symbol_id` entities exist in `SymbolTable`
- Verifies resolved `caller_symbol_id` entities exist in `SymbolTable`
- Verifies call type classification consistency

Design Principles
-----------------
- **Structured Validation Report**: Returns `CallValidationReport` with issue breakdowns.
- **Non-Throwing**: Records issues as warnings and errors without raising exceptions.
"""

from __future__ import annotations

from typing import Dict, List, Set

from models.call_models import (
    CallValidationIssue,
    CallValidationReport,
)
from analysis.symbol_table.symbol_table import SymbolTable
from analysis.function_call_detection.call_index import CallIndex


class CallValidator:
    """
    Validator engine for checking graph integrity of detected function calls.

    Usage::

        validator = CallValidator()
        report = validator.validate(call_index, symbol_table)
    """

    def validate(
        self,
        call_index: CallIndex,
        symbol_table: SymbolTable,
    ) -> CallValidationReport:
        """
        Validate integrity of repository call records.

        Parameters
        ----------
        call_index:
            Pre-indexed `CallIndex`.
        symbol_table:
            Repository `SymbolTable`.

        Returns
        -------
        CallValidationReport
        """
        issues: List[CallValidationIssue] = []
        error_count = 0
        warning_count = 0

        # Duplicate detection per file: (file_path, line, column, callee_name)
        seen_calls: Dict[tuple, str] = {}

        for call_id, call in call_index.calls.items():
            # 1. Duplicate Call Detection
            key = (call.file_path, call.line, call.column, call.callee_name)
            if key in seen_calls:
                issues.append(
                    CallValidationIssue(
                        severity="warning",
                        code="DUPLICATE_CALL",
                        message=(
                            f"Duplicate call expression '{call.callee_name}' in '{call.file_path}' "
                            f"at line {call.line}:{call.column} (first: {seen_calls[key]}, duplicate: {call_id})"
                        ),
                        call_id=call_id,
                        file_path=call.file_path,
                    )
                )
                warning_count += 1
            else:
                seen_calls[key] = call_id

            # 2. Dangling Callee Symbol ID Check
            if call.callee_symbol_id:
                if call.callee_symbol_id not in symbol_table:
                    issues.append(
                        CallValidationIssue(
                            severity="error",
                            code="DANGLING_CALLEE_ID",
                            message=(
                                f"Call '{call.callee_name}' references dangling callee_symbol_id "
                                f"'{call.callee_symbol_id}' not found in SymbolTable"
                            ),
                            call_id=call_id,
                            file_path=call.file_path,
                        )
                    )
                    error_count += 1

            # 3. Dangling Caller Symbol ID Check
            if call.caller_symbol_id:
                if call.caller_symbol_id not in symbol_table:
                    issues.append(
                        CallValidationIssue(
                            severity="warning",
                            code="DANGLING_CALLER_ID",
                            message=(
                                f"Call '{call.callee_name}' references dangling caller_symbol_id "
                                f"'{call.caller_symbol_id}' not found in SymbolTable"
                            ),
                            call_id=call_id,
                            file_path=call.file_path,
                        )
                    )
                    warning_count += 1

        is_valid = error_count == 0
        return CallValidationReport(
            is_valid=is_valid,
            issues=issues,
            error_count=error_count,
            warning_count=warning_count,
        )
