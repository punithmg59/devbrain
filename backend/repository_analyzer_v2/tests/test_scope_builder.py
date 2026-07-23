"""
tests/test_scope_builder.py
-----------------------------
Unit tests for ScopeBuilder scope tree construction and shadowing detection.
"""

from models.ast import NodeLocation, NodeRange
from models.semantic import ExtractedClass, ExtractedFunction, ExtractedModule, ExtractedParameter, ExtractedVariable, VariableScope
from models.symbol import SymbolKind
from analysis.symbol_table.symbol_builder import SymbolTableBuilder
from analysis.scope_resolution.scope_builder import ScopeBuilder
from analysis.scope_resolution.scope_tree import ScopeTree


def make_range(start_line: int, end_line: int) -> NodeRange:
    return NodeRange(
        start=NodeLocation(line=start_line, column=0),
        end=NodeLocation(line=end_line, column=10),
        start_byte=0,
        end_byte=100,
    )


class TestScopeBuilder:
    def test_build_module_and_function_scopes(self):
        mod = ExtractedModule(
            name="app.core",
            file_path="app/core.py",
            functions=[
                ExtractedFunction(
                    name="calculate",
                    parameters=[ExtractedParameter(name="x", annotation="int")],
                    local_variables=[ExtractedVariable(name="total", scope=VariableScope.LOCAL)],
                    range=make_range(5, 15),
                )
            ],
            global_variables=[ExtractedVariable(name="PI", scope=VariableScope.GLOBAL)],
        )

        sym_builder = SymbolTableBuilder(repository_id="repo1")
        symbol_table = sym_builder.build_from_module(mod)

        scope_builder = ScopeBuilder(repository_id="repo1")
        tree, shadowing = scope_builder.build_from_module(mod, symbol_table)

        assert len(tree) == 2  # Module scope + Function scope
        mod_scope = next(s for s in tree.scopes.values() if s.kind == "module")
        func_scope = next(s for s in tree.scopes.values() if s.kind == "function")

        assert func_scope.parent_id == mod_scope.id
        assert len(func_scope.defined_symbol_ids) >= 2  # Param x + Local total

    def test_shadowing_detection(self):
        mod = ExtractedModule(
            name="app.shadow",
            file_path="app/shadow.py",
            global_variables=[
                ExtractedVariable(name="x", scope=VariableScope.GLOBAL, value_snippet="10")
            ],
            functions=[
                ExtractedFunction(
                    name="test",
                    parameters=[ExtractedParameter(name="x", annotation="int")],  # x shadows global x
                    range=make_range(3, 8),
                )
            ],
        )

        sym_builder = SymbolTableBuilder(repository_id="repo1")
        symbol_table = sym_builder.build_from_module(mod)

        scope_builder = ScopeBuilder(repository_id="repo1")
        tree, shadowing = scope_builder.build_from_module(mod, symbol_table)

        assert len(shadowing) == 1
        sh = shadowing[0]
        assert sh.name == "x"

    def test_class_and_method_scopes(self):
        mod = ExtractedModule(
            name="app.models",
            file_path="app/models.py",
            classes=[
                ExtractedClass(
                    name="User",
                    class_attributes=[ExtractedVariable(name="table_name", scope=VariableScope.CLASS_ATTRIBUTE)],
                    methods=[ExtractedFunction(name="save")],
                )
            ],
        )

        sym_builder = SymbolTableBuilder(repository_id="repo1")
        symbol_table = sym_builder.build_from_module(mod)

        scope_builder = ScopeBuilder(repository_id="repo1")
        tree, shadowing = scope_builder.build_from_module(mod, symbol_table)

        assert len(tree) == 3  # Module + Class + Method
        cls_scope = next(s for s in tree.scopes.values() if s.kind == "class")
        method_scope = next(s for s in tree.scopes.values() if s.kind in ("function", "method"))

        assert method_scope.parent_id == cls_scope.id
