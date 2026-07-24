"""
tests/test_call_builder.py
---------------------------
Unit tests for CallBuilder — extracting CallRecord instances from AST nodes and semantic modules.
"""

from models.ast import ASTNode, ASTRoot, NodeLocation, NodeMetadata, NodeRange, NodeType
from models.semantic import (
    ExtractedClass,
    ExtractedDecorator,
    ExtractedFunction,
    ExtractedModule,
    ExtractedVariable,
    SemanticExtractionResult,
    VariableScope,
)
from analysis.symbol_table.symbol_builder import SymbolTableBuilder
from analysis.scope_resolution.scope_builder import ScopeBuilder
from analysis.function_call_detection.call_builder import CallBuilder


def _make_range(line=1, col=0):
    return NodeRange(
        start=NodeLocation(line=line, column=col),
        end=NodeLocation(line=line, column=col + 10),
    )


class TestCallBuilder:
    def test_extract_call_from_ast_node(self):
        root = ASTNode(
            type=NodeType.MODULE,
            range=_make_range(1, 0),
            children=[
                ASTNode(
                    type=NodeType.CALL,
                    name="login",
                    range=_make_range(5, 4),
                )
            ],
        )
        ast_root = ASTRoot(file_path="app/auth.py", language="python", root_node=root)

        mod = ExtractedModule(name="app.auth", file_path="app/auth.py")
        sem_res = SemanticExtractionResult(file_path="app/auth.py", language="python", module=mod)
        sym_builder = SymbolTableBuilder(repository_id="repo1")
        symbol_table = sym_builder.build_from_results([sem_res])
        scope_builder = ScopeBuilder(repository_id="repo1")
        scope_tree, _ = scope_builder.build_from_module(mod, symbol_table)

        builder = CallBuilder(repository_id="repo1")
        records = builder.build_from_ast(ast_root, "app/auth.py", symbol_table, scope_tree)

        assert len(records) == 1
        rec = records[0]
        assert rec.callee_name == "login"
        assert rec.line == 5
        assert rec.file_path == "app/auth.py"

    def test_extract_nested_and_method_calls_from_ast(self):
        """save(validate(user)) and user.login()"""
        call_validate = ASTNode(type=NodeType.CALL, name="validate", range=_make_range(10, 8))
        call_save = ASTNode(
            type=NodeType.CALL,
            name="save",
            range=_make_range(10, 4),
            children=[call_validate],
        )
        call_method = ASTNode(type=NodeType.CALL, name="user.login", range=_make_range(12, 4))

        root = ASTNode(
            type=NodeType.MODULE,
            range=_make_range(1, 0),
            children=[call_save, call_method],
        )
        ast_root = ASTRoot(file_path="main.py", language="python", root_node=root)

        mod = ExtractedModule(name="main", file_path="main.py")
        sem_res = SemanticExtractionResult(file_path="main.py", language="python", module=mod)
        symbol_table = SymbolTableBuilder(repository_id="repo1").build_from_results([sem_res])
        scope_tree, _ = ScopeBuilder(repository_id="repo1").build_from_module(mod, symbol_table)

        builder = CallBuilder(repository_id="repo1")
        records = builder.build_from_ast(ast_root, "main.py", symbol_table, scope_tree)

        assert len(records) == 3
        names = [r.callee_name for r in records]
        assert "save" in names
        assert "validate" in names
        assert "user.login" in names

    def test_fallback_semantic_module_scanner(self):
        """Verifies call extraction from ExtractedModule local variables when AST is None."""
        mod = ExtractedModule(
            name="app.main",
            file_path="app/main.py",
            functions=[
                ExtractedFunction(
                    name="run",
                    range=_make_range(2, 0),
                    local_variables=[
                        ExtractedVariable(
                            name="user",
                            scope=VariableScope.LOCAL,
                            inferred_expression_kind="call",
                            value_snippet="User()",
                            range=_make_range(3, 4),
                        ),
                        ExtractedVariable(
                            name="res",
                            scope=VariableScope.LOCAL,
                            inferred_expression_kind="call",
                            value_snippet="await service.fetch()",
                            range=_make_range(4, 4),
                        ),
                    ],
                )
            ],
        )
        sem_res = SemanticExtractionResult(file_path="app/main.py", language="python", module=mod)
        symbol_table = SymbolTableBuilder(repository_id="repo1").build_from_results([sem_res])
        scope_tree, _ = ScopeBuilder(repository_id="repo1").build_from_module(mod, symbol_table)

        builder = CallBuilder(repository_id="repo1")
        records = builder.build_from_module(mod, symbol_table, scope_tree)

        assert len(records) == 2
        callees = [r.callee_name for r in records]
        assert "User" in callees
        assert "service.fetch" in callees

        async_calls = [r for r in records if r.is_async]
        assert len(async_calls) == 1
        assert async_calls[0].callee_name == "service.fetch"
