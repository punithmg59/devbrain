"""
tests/test_import_resolver.py
------------------------------
Integration tests for ImportResolver coordinator.
"""

from models.semantic import ExtractedClass, ExtractedFunction, ExtractedImport, ExtractedModule, SemanticExtractionResult
from analysis.symbol_table.symbol_builder import SymbolTableBuilder
from analysis.import_resolution.import_resolver import ImportResolver
from models.import_models import ImportResolutionStatus


class TestImportResolver:
    def test_resolve_standard_and_external_imports(self):
        mod = ExtractedModule(
            name="app.main",
            file_path="app/main.py",
            imports=[
                ExtractedImport(module="os"),
                ExtractedImport(module="sys"),
                ExtractedImport(module="requests"),
                ExtractedImport(module="fastapi"),
            ],
        )

        sem_res = SemanticExtractionResult(file_path="app/main.py", language="python", module=mod)

        sym_builder = SymbolTableBuilder(repository_id="repo1")
        symbol_table = sym_builder.build_from_results([sem_res])

        resolver = ImportResolver(repository_id="repo1")
        res = resolver.resolve_result(sem_res, symbol_table)

        assert res.metrics.total_imports == 4
        assert res.metrics.resolved_stdlib == 2
        assert res.metrics.resolved_external == 2

    def test_resolve_internal_cross_file_imports(self):
        mod_auth = ExtractedModule(
            name="app.auth",
            file_path="app/auth.py",
            classes=[ExtractedClass(name="AuthService")],
        )
        mod_user = ExtractedModule(
            name="app.user",
            file_path="app/user.py",
            imports=[
                ExtractedImport(module="app.auth", imported_names=["AuthService"]),
            ],
        )

        res_auth = SemanticExtractionResult(file_path="app/auth.py", language="python", module=mod_auth)
        res_user = SemanticExtractionResult(file_path="app/user.py", language="python", module=mod_user)

        sym_builder = SymbolTableBuilder(repository_id="repo1")
        symbol_table = sym_builder.build_from_results([res_auth, res_user])

        resolver = ImportResolver(repository_id="repo1")
        res = resolver.resolve_results([res_auth, res_user], symbol_table)

        assert res.metrics.resolved_internal == 1
        imp_res = list(res.resolutions.values())[0]
        assert imp_res.status == ImportResolutionStatus.RESOLVED_INTERNAL
        assert imp_res.target_module_fqn == "app.auth"
        assert imp_res.target_symbol_id is not None
        assert imp_res.target_symbol_fqn == "app.auth.AuthService"
