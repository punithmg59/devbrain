"""
tests/test_symbol_builder.py
-----------------------------
Unit tests for SymbolTableBuilder entity transformation.
"""

from models.ast import NodeLocation, NodeRange
from models.semantic import (
    ExtractedClass,
    ExtractedDecorator,
    ExtractedFunction,
    ExtractedImport,
    ExtractedModule,
    ExtractedParameter,
    ExtractedVariable,
    MethodModifier,
    ParameterKind,
    SemanticExtractionResult,
    VariableScope,
)
from models.symbol import SymbolKind, SymbolScope
from analysis.symbol_table.symbol_builder import SymbolTableBuilder


def make_range(start_line: int, end_line: int) -> NodeRange:
    return NodeRange(
        start=NodeLocation(line=start_line, column=0),
        end=NodeLocation(line=end_line, column=10),
        start_byte=0,
        end_byte=100,
    )


class TestSymbolTableBuilder:
    def test_build_from_module_basic(self):
        mod = ExtractedModule(
            name="utils.math",
            file_path="utils/math.py",
            docstring="Math helpers.",
            functions=[
                ExtractedFunction(
                    name="add",
                    parameters=[
                        ExtractedParameter(name="x", annotation="int"),
                        ExtractedParameter(name="y", annotation="int", has_default=True, default_value="0"),
                    ],
                    return_annotation="int",
                    docstring="Add x and y.",
                    range=make_range(5, 10),
                )
            ],
            constants=[
                ExtractedVariable(name="PI", scope=VariableScope.GLOBAL, is_constant=True)
            ],
        )

        builder = SymbolTableBuilder(repository_id="repo1")
        table = builder.build_from_module(mod)

        assert table.is_frozen is True
        assert len(table) >= 5  # Module, Function, 2 Params, 1 Constant

        # Lookup function symbol
        fn_sym = next(s for s in table.symbols.values() if s.kind == SymbolKind.FUNCTION)
        assert fn_sym.name == "add"
        assert fn_sym.fqn == "utils.math.add"
        assert fn_sym.metadata["docstring"] == "Add x and y."

        # Lookup constant symbol
        const_sym = next(s for s in table.symbols.values() if s.kind == SymbolKind.CONSTANT)
        assert const_sym.name == "PI"
        assert const_sym.fqn == "utils.math.PI"

    def test_class_hierarchy_transformation(self):
        mod = ExtractedModule(
            name="services.auth",
            file_path="services/auth.py",
            classes=[
                ExtractedClass(
                    name="AuthService",
                    docstring="Authentication service.",
                    base_classes=["BaseService"],
                    class_attributes=[
                        ExtractedVariable(name="TIMEOUT", scope=VariableScope.CLASS_ATTRIBUTE, is_constant=True)
                    ],
                    methods=[
                        ExtractedFunction(
                            name="login",
                            method_modifiers=[MethodModifier.INSTANCE],
                            parameters=[
                                ExtractedParameter(name="self"),
                                ExtractedParameter(name="username", annotation="str"),
                            ],
                            range=make_range(10, 20),
                        )
                    ],
                    range=make_range(1, 30),
                )
            ],
        )

        builder = SymbolTableBuilder(repository_id="repo1")
        table = builder.build_from_module(mod)

        cls_sym = next(s for s in table.symbols.values() if s.kind == SymbolKind.CLASS)
        assert cls_sym.fqn == "services.auth.AuthService"
        assert cls_sym.metadata["base_classes"] == ["BaseService"]

        method_sym = next(s for s in table.symbols.values() if s.kind == SymbolKind.METHOD)
        assert method_sym.fqn == "services.auth.AuthService.login"
        assert method_sym.parent_id == cls_sym.id

    def test_imports_and_decorators_transformation(self):
        mod = ExtractedModule(
            name="controllers.user",
            file_path="controllers/user.py",
            imports=[
                ExtractedImport(
                    module="typing",
                    imported_names=["List", "Dict"],
                    aliases={"Dict": "Map"},
                )
            ],
            functions=[
                ExtractedFunction(
                    name="get_users",
                    decorators=[
                        ExtractedDecorator(expression="@app.get('/users')", name="app.get", arguments=["'/users'"])
                    ],
                )
            ],
        )

        builder = SymbolTableBuilder(repository_id="repo1")
        table = builder.build_from_module(mod)

        imp_sym = next(s for s in table.symbols.values() if s.kind == SymbolKind.IMPORT)
        assert imp_sym.name == "typing"
        assert imp_sym.metadata["aliases"] == {"Dict": "Map"}

        dec_sym = next(s for s in table.symbols.values() if s.kind == SymbolKind.DECORATOR)
        assert dec_sym.name == "app.get"

    def test_duplicate_symbol_detection(self):
        mod = ExtractedModule(
            name="app.main",
            file_path="app/main.py",
            functions=[
                ExtractedFunction(name="process"),
                ExtractedFunction(name="process"),  # Duplicate function name in same module
            ],
        )

        builder = SymbolTableBuilder(repository_id="repo1")
        table = builder.build_from_module(mod)

        assert table.metrics.duplicate_count == 1
