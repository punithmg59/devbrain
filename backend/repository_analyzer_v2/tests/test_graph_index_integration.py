"""
tests/test_graph_index_integration.py
--------------------------------------
End-to-end integration tests for Phase 4.8.2 Graph Index & Query Engine.

Exercises full pipeline execution:
SemanticExtractionResult -> SymbolTable -> ScopeTree -> ImportResolution -> ReferenceResolution -> FunctionCallDetector -> CallGraphBuilder -> GraphIndex & QueryEngine
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
from analysis.call_graph.graph_index import CallGraphIndexBuilder


def _make_range(line=1, col=0):
    return NodeRange(
        start=NodeLocation(line=line, column=col),
        end=NodeLocation(line=line, column=col + 10),
    )


def _sem(file_path: str, module: ExtractedModule) -> SemanticExtractionResult:
    return SemanticExtractionResult(file_path=file_path, language="python", module=module)


class TestGraphIndexIntegration:
    def test_e2e_graph_indexing_and_querying_pipeline(self):
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
            functions=[ExtractedFunction(name="main", range=_make_range(6, 0))],
        )

        sem_auth = _sem("auth.py", mod_auth)
        sem_user = _sem("user.py", mod_user)
        sem_results = [sem_auth, sem_user]

        # 1. Symbol Table
        symbol_table = SymbolTableBuilder(repository_id="test-idx-e2e").build_from_results(sem_results)

        # 2. Scope Resolution
        scope_res = ScopeResolver(repository_id="test-idx-e2e").resolve_results(sem_results, symbol_table)
        scope_tree = ScopeTree(repository_id="test-idx-e2e", scopes=scope_res.scopes, root_scope_ids=scope_res.root_scope_ids)

        # 3. Import Resolution
        import_res = ImportResolver(repository_id="test-idx-e2e").resolve_results(sem_results, symbol_table)

        # 4. Reference Resolution
        ref_res = ReferenceResolver(repository_id="test-idx-e2e").resolve_results(sem_results, symbol_table, scope_tree, import_res)

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
        call_res = FunctionCallDetector(repository_id="test-idx-e2e").detect_results(
            extraction_results=sem_results,
            symbol_table=symbol_table,
            scope_tree=scope_tree,
            import_res_result=import_res,
            reference_res_result=ref_res,
            ast_roots={"user.py": ast_user},
        )

        # 7. Call Graph Builder (Phase 4.8.1)
        cg_result = CallGraphBuilder(repository_id="test-idx-e2e").build_graph(call_res, symbol_table)

        # 8. Graph Index & Query Engine (Phase 4.8.2)
        idx_builder = CallGraphIndexBuilder(repository_id="test-idx-e2e")
        idx_result = idx_builder.build_index(cg_result)

        assert idx_result.validation_report.is_valid
        assert idx_result.metrics.indexed_nodes >= 3
        assert idx_result.metrics.indexed_edges >= 2

        engine = idx_result.query_engine

        # Verify O(1) query lookups
        login_node = engine.find_node_by_fqn("auth.login")
        assert login_node is not None
        assert login_node.name == "login"

        user_nodes = engine.find_nodes_by_file("user.py")
        assert len(user_nodes) >= 2

        main_node = engine.find_node_by_fqn("user.main")
        assert main_node is not None

        callers_of_login = engine.find_callers(login_node.symbol_id)
        assert main_node.symbol_id in callers_of_login

        callees_of_main = engine.find_callees(main_node.symbol_id)
        assert login_node.symbol_id in callees_of_main

        assert engine.contains_edge(main_node.symbol_id, login_node.symbol_id)
