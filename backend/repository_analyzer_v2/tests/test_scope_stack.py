"""
tests/test_scope_stack.py
--------------------------
Unit tests for ScopeStack LIFO tracker and shadowing detection.
"""

import pytest
from models.scope import Scope, ScopeKind
from models.symbol import Symbol, SymbolKind
from analysis.symbol_table.symbol_table import SymbolTable
from analysis.scope_resolution.scope_stack import ScopeStack


class TestScopeStack:
    def test_stack_push_pop_depth(self):
        stack = ScopeStack()
        assert stack.is_empty() is True
        assert stack.depth == 0

        s1 = Scope(id="s1", name="mod", kind=ScopeKind.MODULE)
        s2 = Scope(id="s2", name="func", kind=ScopeKind.FUNCTION, parent_id="s1")

        stack.push_scope(s1)
        assert stack.depth == 1
        assert stack.current_scope() == s1

        stack.push_scope(s2)
        assert stack.depth == 2
        assert stack.current_scope() == s2

        popped = stack.pop_scope()
        assert popped == s2
        assert stack.depth == 1

        popped1 = stack.pop_scope()
        assert popped1 == s1
        assert stack.is_empty() is True

    def test_pop_empty_stack_raises(self):
        stack = ScopeStack()
        with pytest.raises(RuntimeError, match="Cannot pop from an empty ScopeStack"):
            stack.pop_scope()

    def test_resolve_visible_symbol_inner_to_outer(self):
        symbol_table = SymbolTable()
        sym_outer = Symbol(id="sym-g", fqn="app.var", name="var", kind=SymbolKind.VARIABLE, file_path="app.py")
        sym_inner = Symbol(id="sym-l", fqn="app.func.var", name="var", kind=SymbolKind.VARIABLE, file_path="app.py")

        symbol_table.add_symbol(sym_outer)
        symbol_table.add_symbol(sym_inner)

        s_outer = Scope(id="s-outer", name="mod", kind=ScopeKind.MODULE, defined_symbol_ids=["sym-g"])
        s_inner = Scope(id="s-inner", name="func", kind=ScopeKind.FUNCTION, parent_id="s-outer", defined_symbol_ids=["sym-l"])

        stack = ScopeStack()
        stack.push_scope(s_outer)
        stack.push_scope(s_inner)

        visible = stack.resolve_visible_symbol("var", symbol_table)
        assert visible == sym_inner

    def test_check_shadowing(self):
        symbol_table = SymbolTable()
        sym_outer = Symbol(id="sym-g", fqn="app.x", name="x", kind=SymbolKind.VARIABLE, file_path="app.py")
        sym_inner = Symbol(id="sym-l", fqn="app.func.x", name="x", kind=SymbolKind.VARIABLE, file_path="app.py")

        symbol_table.add_symbol(sym_outer)
        symbol_table.add_symbol(sym_inner)

        s_outer = Scope(id="s-outer", name="mod", kind=ScopeKind.MODULE, defined_symbol_ids=["sym-g"])
        s_inner = Scope(id="s-inner", name="func", kind=ScopeKind.FUNCTION, parent_id="s-outer", defined_symbol_ids=["sym-l"])

        stack = ScopeStack()
        stack.push_scope(s_outer)
        stack.push_scope(s_inner)

        shadow = stack.check_shadowing("x", "sym-l", symbol_table)
        assert shadow is not None
        assert shadow.name == "x"
        assert shadow.shadowing_symbol_id == "sym-l"
        assert shadow.shadowed_symbol_id == "sym-g"
