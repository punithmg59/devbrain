"""
tests/test_call_integration.py
-------------------------------
End-to-end integration tests for Phase 4.7.2 Function Call Detection Engine.

Exercises full pipeline integration:
SemanticExtractionResult -> SymbolTable -> ScopeTree -> ImportResolutionResult -> ReferenceResolutionResult -> FunctionCallDetector
"""

from models.semantic import (
    ExtractedClass,
    ExtractedFunction,
    ExtractedImport,
    ExtractedModule,
    ExtractedVariable,
    SemanticExtractionResult,
    VariableScope,
)
from models.ast import ASTNode, ASTRoot, NodeLocation, NodeRange, NodeType
from models.call_models import CallType
from analysis.symbol_table.symbol_builder import SymbolTableBuilder
from analysis.scope_resolution.scope_builder import ScopeBuilder
from analysis.import_resolution.import_resolver import ImportResolver
from analysis.reference_resolution.reference_resolver import ReferenceResolver
from analysis.function_call_detection.call_detector import FunctionCallDetector


def _make_range(line=1, col=0):
    return NodeRange(
        start=NodeLocation(line=line, column=col),
        end=NodeLocation(line=line, column=col + 10),
    )


def _sem(file_path: str, module: ExtractedModule) -> SemanticExtractionResult:
    return SemanticExtractionResult(file_path=file_path, language="python", module=module)


class TestFunctionCallDetectionIntegration:
    def test_e2e_function_call_detection_pipeline(self):
        """
        Simulates:
        auth.py:
            def login(): pass
        user.py:
            from auth import login
            class User:
                def __init__(self): pass
            def main():
                login()
                u = User()
        """
        mod_auth = ExtractedModule(
            name="auth",
            file_path="auth.py",
            functions=[ExtractedFunction(name="login", range=_make_range(1, 0))],
        )
        mod_user = ExtractedModule(
            name="user",
            file_path="user.py",
            imports=[ExtractedImport(module="auth", imported_names=["login"])],
            classes=[ExtractedClass(name="User", range=_make_range(3, 0))],
            functions=[
                ExtractedFunction(
                    name="main",
                    range=_make_range(6, 0),
                    local_variables=[
                        ExtractedVariable(
                            name="u",
                            scope=VariableScope.LOCAL,
                            inferred_expression_kind="call",
                            value_snippet="User()",
                            range=_make_range(8, 4),
                        )
                    ],
                )
            ],
        )

        sem_auth = _sem("auth.py", mod_auth)
        sem_user = _sem("user.py", mod_user)
        sem_results = [sem_auth, sem_user]

        # 1. Symbol Table
        sym_builder = SymbolTableBuilder(repository_id="test-e2e")
        symbol_table = sym_builder.build_from_results(sem_results)

        # 2. Scope Resolution
        from analysis.scope_resolution.scope_resolver import ScopeResolver
        scope_resolver = ScopeResolver(repository_id="test-e2e")
        scope_res = scope_resolver.resolve_results(sem_results, symbol_table)
        from analysis.scope_resolution.scope_tree import ScopeTree
        scope_tree = ScopeTree(repository_id="test-e2e", scopes=scope_res.scopes, root_scope_ids=scope_res.root_scope_ids)

        # 3. Import Resolution
        import_resolver = ImportResolver(repository_id="test-e2e")
        import_res = import_resolver.resolve_results(sem_results, symbol_table)

        # 4. Reference Resolution
        ref_resolver = ReferenceResolver(repository_id="test-e2e")
        ref_res = ref_resolver.resolve_results(sem_results, symbol_table, scope_tree, import_res)

        # 5. AST for user.py
        call_login_ast = ASTNode(type=NodeType.CALL, name="login", range=_make_range(7, 4))
        call_user_ast = ASTNode(type=NodeType.CALL, name="User", range=_make_range(8, 8))
        fn_main_ast = ASTNode(
            type=NodeType.FUNCTION,
            name="main",
            range=_make_range(6, 0),
            children=[call_login_ast, call_user_ast],
        )
        root_user_ast = ASTNode(type=NodeType.MODULE, range=_make_range(1, 0), children=[fn_main_ast])
        ast_user = ASTRoot(file_path="user.py", language="python", root_node=root_user_ast)

        ast_roots = {"user.py": ast_user}

        # 6. Function Call Detector
        detector = FunctionCallDetector(repository_id="test-e2e")
        call_res = detector.detect_results(
            extraction_results=sem_results,
            symbol_table=symbol_table,
            scope_tree=scope_tree,
            import_res_result=import_res,
            reference_res_result=ref_res,
            ast_roots=ast_roots,
        )

        assert call_res.metrics.total_calls >= 2
        assert call_res.validation_report.is_valid

        # Check call resolutions
        call_list = list(call_res.calls.values())
        callee_names = [c.callee_name for c in call_list]
        assert "login" in callee_names
        assert "User" in callee_names

        login_call = next(c for c in call_list if c.callee_name == "login")
        assert login_call.callee_symbol_id is not None
        assert login_call.callee_fqn == "auth.login"

        user_call = next(c for c in call_list if c.callee_name == "User")
        assert user_call.callee_symbol_id is not None
        assert user_call.is_constructor
        assert user_call.call_type == CallType.CONSTRUCTOR
