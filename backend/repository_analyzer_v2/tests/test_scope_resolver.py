"""
tests/test_scope_resolver.py
-----------------------------
Integration tests for ScopeResolver coordinator.
"""

from models.semantic import ExtractedClass, ExtractedFunction, ExtractedModule, ExtractedVariable, SemanticExtractionResult, VariableScope
from analysis.symbol_table.symbol_table import SymbolTable
from analysis.symbol_table.symbol_builder import SymbolTableBuilder
from analysis.scope_resolution.scope_resolver import ScopeResolver


class TestScopeResolver:
    def test_resolve_single_module(self):
        mod = ExtractedModule(
            name="app.service",
            file_path="app/service.py",
            classes=[
                ExtractedClass(
                    name="AuthService",
                    methods=[ExtractedFunction(name="authenticate")],
                )
            ],
            global_variables=[ExtractedVariable(name="SECRET_KEY", scope=VariableScope.GLOBAL)],
        )

        sem_result = SemanticExtractionResult(
            file_path="app/service.py",
            language="python",
            module=mod,
        )

        sym_builder = SymbolTableBuilder(repository_id="repo1")
        symbol_table = sym_builder.build_from_results([sem_result])

        resolver = ScopeResolver(repository_id="repo1")
        res = resolver.resolve_result(sem_result, symbol_table)

        assert res.repository_id == "repo1"
        assert len(res.scopes) >= 3  # Module + Class + Method
        assert res.metrics.total_scopes == len(res.scopes)
        assert res.metrics.build_duration_ms >= 0.0

    def test_resolve_multiple_modules(self):
        mod1 = ExtractedModule(name="mod1", file_path="mod1.py", functions=[ExtractedFunction(name="fn1")])
        mod2 = ExtractedModule(name="mod2", file_path="mod2.py", functions=[ExtractedFunction(name="fn2")])

        res1 = SemanticExtractionResult(file_path="mod1.py", language="python", module=mod1)
        res2 = SemanticExtractionResult(file_path="mod2.py", language="python", module=mod2)

        sym_builder = SymbolTableBuilder(repository_id="repo1")
        symbol_table = sym_builder.build_from_results([res1, res2])

        resolver = ScopeResolver(repository_id="repo1")
        result = resolver.resolve_results([res1, res2], symbol_table)

        assert len(result.root_scope_ids) == 2
        assert len(result.scopes) == 4  # 2 modules + 2 functions
