"""
tests/test_reference_validator.py
----------------------------------
Unit tests for ReferenceValidator reference binding integrity validator.
"""

from models.reference_models import (
    ReferenceKind,
    ReferenceRecord,
    ReferenceResolution,
)
from analysis.scope_resolution.scope_tree import ScopeTree
from analysis.symbol_table.symbol_table import SymbolTable
from analysis.reference_resolution.reference_index import ReferenceIndex
from analysis.reference_resolution.reference_validator import ReferenceValidator


class TestReferenceValidator:
    def test_clean_references_are_valid(self):
        ref_index = ReferenceIndex()
        symbol_table = SymbolTable()
        scope_tree = ScopeTree()

        rec = ReferenceRecord(
            id="ref-1",
            file_path="app.py",
            symbol_id=None,  # Unresolved reference triggers warning
            symbol_name="x",
            kind=ReferenceKind.VARIABLE_READ,
            scope_id="root",
            line=5,
            column=0,
            end_line=5,
            end_column=2,
            is_read=True,
        )
        res = ReferenceResolution(
            reference_id="ref-1",
            symbol_id=None,
            scope_id="root",
            is_resolved=False,
        )
        ref_index.add_reference(rec, res)

        validator = ReferenceValidator()
        report = validator.validate(ref_index, symbol_table, scope_tree)

        # Unresolved reference is a warning, so error_count == 0 and is_valid is True
        assert report.is_valid is True
        assert report.warning_count == 1
        assert report.issues[0].code == "UNRESOLVED_REFERENCE"

    def test_detect_dangling_symbol_id_error(self):
        ref_index = ReferenceIndex()
        symbol_table = SymbolTable()
        scope_tree = ScopeTree()

        rec = ReferenceRecord(
            id="ref-bad",
            file_path="app.py",
            symbol_id="non-existent-sym-id",
            symbol_name="AuthService",
            kind=ReferenceKind.CLASS_DEFINITION,
            scope_id="root",
            line=5,
            column=0,
            end_line=5,
            end_column=15,
            is_definition=True,
        )
        res = ReferenceResolution(
            reference_id="ref-bad",
            symbol_id="non-existent-sym-id",
            scope_id="root",
            is_resolved=True,
        )
        ref_index.add_reference(rec, res)

        validator = ReferenceValidator()
        report = validator.validate(ref_index, symbol_table, scope_tree)

        assert report.is_valid is False
        assert report.error_count == 1
        assert report.issues[0].code == "DANGLING_SYMBOL_ID"
