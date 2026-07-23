"""
tests/test_import_index.py
---------------------------
Unit tests for ImportIndex multi-index lookups.
"""

from models.import_models import (
    ImportKind,
    ImportRecord,
    ImportResolution,
    ImportResolutionStatus,
)
from analysis.import_resolution.import_index import ImportIndex


class TestImportIndex:
    def test_multi_index_lookups(self):
        index = ImportIndex()

        rec = ImportRecord(
            id="imp-1",
            kind=ImportKind.FROM_IMPORT,
            statement_snippet="from app.auth import AuthService",
            source_file_path="app/user.py",
            source_module_fqn="app.user",
            imported_module_name="app.auth",
            imported_symbol_name="AuthService",
        )
        res = ImportResolution(
            import_id="imp-1",
            status=ImportResolutionStatus.RESOLVED_INTERNAL,
            target_module_fqn="app.auth",
            target_file_path="app/auth.py",
            target_symbol_id="sym-auth-service",
            target_symbol_fqn="app.auth.AuthService",
        )

        index.add_import(rec, res)

        assert len(index) == 1
        assert index.get_imports_by_file("app/user.py") == [rec]
        assert index.get_imports_by_source_module("app.user") == [rec]
        assert index.get_imports_by_target_module("app.auth") == [rec]
        assert index.get_imports_by_target_symbol_id("sym-auth-service") == [rec]
        assert index.get_imports_by_status(ImportResolutionStatus.RESOLVED_INTERNAL) == [rec]
