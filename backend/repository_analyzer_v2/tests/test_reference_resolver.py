"""
tests/test_reference_resolver.py
---------------------------------
Integration tests for ReferenceResolver coordinator.
"""

from models.semantic import ExtractedClass, ExtractedFunction, ExtractedModule, SemanticExtractionResult
from analysis.symbol_table.symbol_builder import SymbolTableBuilder
from analysis.scope_resolution.scope_resolver import ScopeResolver
from analysis.reference_resolution.reference_resolver import ReferenceResolver


class TestReferenceResolver:
    def test_resolve_references_single_module(self):
        mod = ExtractedModule(
            name="app.auth",
            file_path="app/auth.py",
            classes=[
                ExtractedClass(
                    name="AuthService",
                    methods=[ExtractedFunction(name="authenticate")],
                )
            ],
        )

        sem_res = SemanticExtractionResult(file_path="app/auth.py", language="python", module=mod)

        sym_builder = SymbolTableBuilder(repository_id="repo1")
        symbol_table = sym_builder.build_from_results([sem_res])

        scope_resolver = ScopeResolver(repository_id="repo1")
        scope_res = scope_resolver.resolve_result(sem_res, symbol_table)

        # Convert dictionary to ScopeTree
        from analysis.scope_resolution.scope_tree import ScopeTree
        tree = ScopeTree(repository_id="repo1", scopes=scope_res.scopes, root_scope_ids=scope_res.root_scope_ids)

        ref_resolver = ReferenceResolver(repository_id="repo1")
        ref_res = ref_resolver.resolve_result(sem_res, symbol_table, tree)

        assert ref_res.repository_id == "repo1"
        assert len(ref_res.references) >= 3  # Module + Class + Method
        assert ref_res.metrics.total_references == len(ref_res.references)
        assert ref_res.metrics.resolved_count >= 3
