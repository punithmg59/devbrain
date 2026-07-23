"""
tests/test_reference_builder.py
--------------------------------
Unit tests for ReferenceBuilder reference extraction and symbol binding.
"""

from models.semantic import ExtractedClass, ExtractedFunction, ExtractedModule, ExtractedParameter, ExtractedVariable, VariableScope
from analysis.symbol_table.symbol_builder import SymbolTableBuilder
from analysis.scope_resolution.scope_builder import ScopeBuilder
from analysis.reference_resolution.reference_builder import ReferenceBuilder


class TestReferenceBuilder:
    def test_build_references_from_module(self):
        mod = ExtractedModule(
            name="app.service",
            file_path="app/service.py",
            classes=[
                ExtractedClass(
                    name="UserService",
                    methods=[
                        ExtractedFunction(
                            name="login",
                            parameters=[ExtractedParameter(name="username")],
                            local_variables=[ExtractedVariable(name="token", scope=VariableScope.LOCAL)],
                        )
                    ],
                )
            ],
            global_variables=[ExtractedVariable(name="CONFIG", scope=VariableScope.GLOBAL)],
        )

        sym_builder = SymbolTableBuilder(repository_id="repo1")
        symbol_table = sym_builder.build_from_module(mod)

        scope_builder = ScopeBuilder(repository_id="repo1")
        scope_tree, _ = scope_builder.build_from_module(mod, symbol_table)

        ref_builder = ReferenceBuilder(repository_id="repo1")
        records, resolutions = ref_builder.build_from_module(mod, symbol_table, scope_tree)

        assert len(records) >= 5
        sym_names = [r.symbol_name for r in records]
        assert "UserService" in sym_names
        assert "login" in sym_names
        assert "username" in sym_names
        assert "token" in sym_names
        assert "CONFIG" in sym_names

        # Check resolution binding
        resolved_count = sum(1 for r in resolutions if r.is_resolved)
        assert resolved_count >= 5
