"""
tests/test_import_validator.py
-------------------------------
Unit tests for ImportValidator import graph integrity validator.
"""

from models.import_models import (
    ImportKind,
    ImportRecord,
    ImportResolution,
    ImportResolutionStatus,
)
from analysis.symbol_table.symbol_table import SymbolTable
from analysis.import_resolution.import_index import ImportIndex
from analysis.import_resolution.import_validator import ImportValidator
from analysis.import_resolution.module_index import ModuleIndex


class TestImportValidator:
    def test_clean_imports_are_valid(self):
        import_index = ImportIndex()
        module_index = ModuleIndex()
        symbol_table = SymbolTable()

        rec = ImportRecord(
            id="imp-1",
            kind=ImportKind.MODULE,
            statement_snippet="import os",
            source_file_path="app.py",
            source_module_fqn="app",
            imported_module_name="os",
        )
        res = ImportResolution(
            import_id="imp-1",
            status=ImportResolutionStatus.RESOLVED_STDLIB,
            target_module_fqn="os",
            is_stdlib=True,
        )
        import_index.add_import(rec, res)

        validator = ImportValidator()
        report = validator.validate(import_index, module_index, symbol_table)

        assert report.is_valid is True
        assert report.error_count == 0

    def test_detect_missing_module_error(self):
        import_index = ImportIndex()
        module_index = ModuleIndex()
        symbol_table = SymbolTable()

        rec = ImportRecord(
            id="imp-bad",
            kind=ImportKind.MODULE,
            statement_snippet="from non_existent import something",
            source_file_path="app.py",
            source_module_fqn="app",
            imported_module_name="non_existent",
        )
        res = ImportResolution(
            import_id="imp-bad",
            status=ImportResolutionStatus.UNRESOLVED_MODULE,
            error_message="Module non_existent not found",
        )
        import_index.add_import(rec, res)

        validator = ImportValidator()
        report = validator.validate(import_index, module_index, symbol_table)

        assert report.is_valid is False
        assert report.error_count == 1
        assert report.issues[0].code == "MISSING_MODULE"

    def test_detect_missing_symbol_error(self):
        import_index = ImportIndex()
        module_index = ModuleIndex()
        symbol_table = SymbolTable()

        rec = ImportRecord(
            id="imp-bad-sym",
            kind=ImportKind.FROM_IMPORT,
            statement_snippet="from app.auth import UnknownSymbol",
            source_file_path="app/user.py",
            source_module_fqn="app.user",
            imported_module_name="app.auth",
            imported_symbol_name="UnknownSymbol",
        )
        res = ImportResolution(
            import_id="imp-bad-sym",
            status=ImportResolutionStatus.UNRESOLVED_SYMBOL,
            target_module_fqn="app.auth",
            error_message="Symbol UnknownSymbol not found in app.auth",
        )
        import_index.add_import(rec, res)

        validator = ImportValidator()
        report = validator.validate(import_index, module_index, symbol_table)

        assert report.is_valid is False
        assert report.error_count == 1
        assert report.issues[0].code == "MISSING_SYMBOL"

    def test_detect_circular_imports(self):
        import_index = ImportIndex()
        module_index = ModuleIndex()
        symbol_table = SymbolTable()

        # File A imports Module B
        rec_a = ImportRecord(id="i1", kind=ImportKind.MODULE, source_file_path="a.py", source_module_fqn="a", imported_module_name="b")
        res_a = ImportResolution(import_id="i1", status=ImportResolutionStatus.RESOLVED_INTERNAL, target_module_fqn="b")
        import_index.add_import(rec_a, res_a)

        # File B imports Module A (Cycle!)
        rec_b = ImportRecord(id="i2", kind=ImportKind.MODULE, source_file_path="b.py", source_module_fqn="b", imported_module_name="a")
        res_b = ImportResolution(import_id="i2", status=ImportResolutionStatus.RESOLVED_INTERNAL, target_module_fqn="a")
        import_index.add_import(rec_b, res_b)

        validator = ImportValidator()
        report = validator.validate(import_index, module_index, symbol_table)

        codes = [i.code for i in report.issues]
        assert "CIRCULAR_IMPORT" in codes
