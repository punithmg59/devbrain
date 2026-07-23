"""
tests/test_scope_tree.py
-------------------------
Unit tests for Scope models and ScopeTree data structures.
"""

from models.scope import Scope, ScopeKind, ScopeLocation
from models.symbol import Symbol, SymbolKind
from analysis.scope_resolution.scope_tree import ScopeTree
from analysis.symbol_table.symbol_table import SymbolTable


class TestScopeModelsAndTree:
    def test_scope_defaults(self):
        scope = Scope(name="module:app", kind=ScopeKind.MODULE, file_path="app.py")
        assert scope.parent_id is None
        assert scope.children_ids == []
        assert scope.defined_symbol_ids == []
        assert scope.visible_symbol_ids == []

    def test_add_scope_and_hierarchy(self):
        tree = ScopeTree(repository_id="repo1")
        mod_scope = Scope(id="s-mod", name="module:app", kind=ScopeKind.MODULE)
        cls_scope = Scope(id="s-cls", name="class:User", kind=ScopeKind.CLASS, parent_id="s-mod")
        func_scope = Scope(id="s-func", name="function:save", kind=ScopeKind.FUNCTION, parent_id="s-cls")

        tree.add_scope(mod_scope)
        tree.add_scope(cls_scope)
        tree.add_scope(func_scope)

        assert len(tree) == 3
        assert tree.root_scope_ids == ["s-mod"]
        assert tree.get_parent_scope("s-func") == cls_scope
        assert tree.get_children_scopes("s-mod") == [cls_scope]

        ancestors = tree.get_ancestor_scopes("s-func")
        anc_ids = [a.id for a in ancestors]
        assert anc_ids == ["s-cls", "s-mod"]

        descendants = tree.get_descendant_scopes("s-mod")
        desc_ids = [d.id for d in descendants]
        assert "s-cls" in desc_ids
        assert "s-func" in desc_ids

    def test_lookup_symbol_in_scope_tree(self):
        symbol_table = SymbolTable()
        g_sym = Symbol(id="sym-x-global", fqn="app.x", name="x", kind=SymbolKind.VARIABLE, file_path="app.py")
        l_sym = Symbol(id="sym-x-local", fqn="app.test.x", name="x", kind=SymbolKind.VARIABLE, file_path="app.py")

        symbol_table.add_symbol(g_sym)
        symbol_table.add_symbol(l_sym)

        tree = ScopeTree()
        mod_scope = Scope(id="s-mod", name="module:app", kind=ScopeKind.MODULE, defined_symbol_ids=["sym-x-global"])
        func_scope = Scope(id="s-func", name="function:test", kind=ScopeKind.FUNCTION, parent_id="s-mod", defined_symbol_ids=["sym-x-local"])

        tree.add_scope(mod_scope)
        tree.add_scope(func_scope)

        # Lookup x from function_scope -> returns local variable
        resolved_local = tree.lookup_symbol("s-func", "x", symbol_table)
        assert resolved_local == l_sym

        # Lookup x from module_scope -> returns global variable
        resolved_global = tree.lookup_symbol("s-mod", "x", symbol_table)
        assert resolved_global == g_sym
