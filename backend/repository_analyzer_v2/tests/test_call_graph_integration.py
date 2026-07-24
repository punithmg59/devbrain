"""
tests/test_call_graph_integration.py
-------------------------------------
End-to-end integration tests for Phase 4.8.1 Call Graph Builder.

Exercises full pipeline execution:
SemanticExtractionResult -> SymbolTable -> ScopeTree -> ImportResolution -> ReferenceResolution -> FunctionCallDetector -> CallGraphBuilder
"""

from models.semantic import (
    ExtractedClass,
    ExtractedFunction,
    ExtractedImport,
    ExtractedModule,
    SemanticExtractionResult,
)
from models.ast import ASTNode, ASTRoot, NodeLocation, NodeRange, NodeType
from analysis.symbol_table.symbol_builder import SymbolTableBuilder
from analysis.scope_resolution.scope_resolver import ScopeResolver
from analysis.scope_resolution.scope_tree import ScopeTree
from analysis.import_resolution.import_resolver import ImportResolver
from analysis.reference_resolution.reference_resolver import ReferenceResolver
from analysis.function_call_detection.call_detector import FunctionCallDetector
from analysis.call_graph.graph_builder import CallGraphBuilder


def _make_range(line=1, col=0):
    return NodeRange(
        start=NodeLocation(line=line, column=col),
        end=NodeLocation(line=line, column=col + 10),
    )


def _sem(file_path: str, module: ExtractedModule) -> SemanticExtractionResult:
    return SemanticExtractionResult(file_path=file_path, language="python", module=module)


class TestCallGraphIntegration:
    def test_e2e_call_graph_building_pipeline(self):
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
                )
            ],
        )

        sem_auth = _sem("auth.py", mod_auth)
        sem_user = _sem("user.py", mod_user)
        sem_results = [sem_auth, sem_user]

        # 1. Symbol Table
        sym_builder = SymbolTableBuilder(repository_id="test-cg-e2e")
        symbol_table = sym_builder.build_from_results(sem_results)

        # 2. Scope Resolution
        scope_resolver = ScopeResolver(repository_id="test-cg-e2e")
        scope_res = scope_resolver.resolve_results(sem_results, symbol_table)
        scope_tree = ScopeTree(repository_id="test-cg-e2e", scopes=scope_res.scopes, root_scope_ids=scope_res.root_scope_ids)

        # 3. Import Resolution
        import_resolver = ImportResolver(repository_id="test-cg-e2e")
        import_res = import_resolver.resolve_results(sem_results, symbol_table)

        # 4. Reference Resolution
        ref_resolver = ReferenceResolver(repository_id="test-cg-e2e")
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

        # 6. Function Call Detector
        detector = FunctionCallDetector(repository_id="test-cg-e2e")
        call_res = detector.detect_results(
            extraction_results=sem_results,
            symbol_table=symbol_table,
            scope_tree=scope_tree,
            import_res_result=import_res,
            reference_res_result=ref_res,
            ast_roots={"user.py": ast_user},
        )

        # 7. Call Graph Builder (Phase 4.8.1)
        cg_builder = CallGraphBuilder(repository_id="test-cg-e2e")
        cg_result = cg_builder.build_graph(call_res, symbol_table)

        assert cg_result.validation_report.is_valid
        assert cg_result.graph.node_count >= 3
        assert cg_result.graph.edge_count >= 2

        # Find main symbol ID
        main_sym = next(s for s in symbol_table.symbols.values() if s.name == "main")
        login_sym = next(s for s in symbol_table.symbols.values() if s.name == "login")
        user_sym = next(s for s in symbol_table.symbols.values() if s.name == "User")

        # Verify directed edges from main -> login and main -> User
        assert main_sym.id in cg_result.graph.adjacency_list
        main_callees = cg_result.graph.adjacency_list[main_sym.id]
        assert login_sym.id in main_callees
        assert user_sym.id in main_callees

        # Verify reverse adjacency
        assert main_sym.id in cg_result.graph.reverse_adjacency_list[login_sym.id]
        assert main_sym.id in cg_result.graph.reverse_adjacency_list[user_sym.id]
