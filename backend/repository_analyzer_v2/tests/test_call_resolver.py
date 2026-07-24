"""
tests/test_call_resolver.py
----------------------------
Unit tests for CallResolver — resolving callee expressions to target callee Symbol IDs.
"""

from models.call_models import CallRecord, CallType
from models.semantic import (
    ExtractedClass,
    ExtractedFunction,
    ExtractedImport,
    ExtractedModule,
    SemanticExtractionResult,
)
from models.symbol import Symbol, SymbolKind
from analysis.symbol_table.symbol_builder import SymbolTableBuilder
from analysis.scope_resolution.scope_builder import ScopeBuilder
from analysis.import_resolution.import_resolver import ImportResolver
from analysis.re_export_resolution.re_export_builder import ReExportBuilder
from analysis.re_export_resolution.re_export_index import ReExportIndex
from analysis.function_call_detection.call_resolver import CallResolver


def _sem(file_path: str, module: ExtractedModule) -> SemanticExtractionResult:
    return SemanticExtractionResult(file_path=file_path, language="python", module=module)


class TestCallResolver:
    def test_resolve_direct_function_call(self):
        mod_auth = ExtractedModule(
            name="app.auth",
            file_path="app/auth.py",
            functions=[ExtractedFunction(name="login")],
        )
        sem_res = _sem("app/auth.py", mod_auth)
        symbol_table = SymbolTableBuilder(repository_id="repo1").build_from_results([sem_res])
        scope_tree, _ = ScopeBuilder(repository_id="repo1").build_from_module(mod_auth, symbol_table)

        call = CallRecord(callee_name="login", file_path="app/auth.py", line=5, column=4)
        resolver = CallResolver()
        resolved = resolver.resolve_call(call, symbol_table, scope_tree)

        assert resolved.callee_symbol_id is not None
        assert resolved.callee_fqn == "app.auth.login"
        assert resolved.call_type == CallType.FUNCTION

    def test_resolve_constructor_call(self):
        mod_user = ExtractedModule(
            name="app.models",
            file_path="app/models.py",
            classes=[ExtractedClass(name="User")],
        )
        sem_res = _sem("app/models.py", mod_user)
        symbol_table = SymbolTableBuilder(repository_id="repo1").build_from_results([sem_res])
        scope_tree, _ = ScopeBuilder(repository_id="repo1").build_from_module(mod_user, symbol_table)

        call = CallRecord(callee_name="User", file_path="app/models.py", line=10, column=4)
        resolver = CallResolver()
        resolved = resolver.resolve_call(call, symbol_table, scope_tree)

        assert resolved.callee_symbol_id is not None
        assert resolved.callee_fqn == "app.models.User"
        assert resolved.is_constructor
        assert resolved.call_type == CallType.CONSTRUCTOR

    def test_resolve_re_exported_constructor_call(self):
        """
        FastAPI pattern:
        fastapi/__init__.py: from .applications import FastAPI
        fastapi/applications.py: class FastAPI
        user_code.py: app = FastAPI()
        """
        mod_init = ExtractedModule(
            name="fastapi",
            file_path="fastapi/__init__.py",
            imports=[
                ExtractedImport(
                    module="applications",
                    imported_names=["FastAPI"],
                    is_relative=True,
                    relative_level=1,
                )
            ],
        )
        mod_app = ExtractedModule(
            name="fastapi.applications",
            file_path="fastapi/applications.py",
            classes=[ExtractedClass(name="FastAPI")],
        )
        mod_user = ExtractedModule(
            name="user_code",
            file_path="user_code.py",
            imports=[ExtractedImport(module="fastapi", imported_names=["FastAPI"])],
        )

        sem_results = [_sem("fastapi/__init__.py", mod_init), _sem("fastapi/applications.py", mod_app), _sem("user_code.py", mod_user)]
        symbol_table = SymbolTableBuilder(repository_id="repo1").build_from_results(sem_results)
        scope_tree, _ = ScopeBuilder(repository_id="repo1").build_from_module(mod_user, symbol_table)

        import_resolver = ImportResolver(repository_id="repo1")
        import_res = import_resolver.resolve_results(sem_results, symbol_table)

        re_exp_builder = ReExportBuilder()
        module_index = import_resolver._linker  # module index built internally
        records = re_exp_builder.build_from_results(sem_results, import_resolver._linker if hasattr(import_resolver, "_linker") else None)
        export_index = ReExportIndex()
        export_index.build(records)

        call = CallRecord(callee_name="FastAPI", file_path="user_code.py", line=3, column=8)
        resolver = CallResolver()
        resolved = resolver.resolve_call(call, symbol_table, scope_tree, import_res, None, export_index)

        assert resolved.callee_symbol_id is not None
        assert resolved.callee_fqn == "fastapi.applications.FastAPI"
        assert resolved.is_constructor

    def test_resolve_builtin_function_as_external(self):
        mod = ExtractedModule(name="main", file_path="main.py")
        sem_res = _sem("main.py", mod)
        symbol_table = SymbolTableBuilder(repository_id="repo1").build_from_results([sem_res])
        scope_tree, _ = ScopeBuilder(repository_id="repo1").build_from_module(mod, symbol_table)

        call = CallRecord(callee_name="print", file_path="main.py", line=2, column=4)
        resolver = CallResolver()
        resolved = resolver.resolve_call(call, symbol_table, scope_tree)

        assert resolved.is_external
        assert resolved.confidence > 0.5
