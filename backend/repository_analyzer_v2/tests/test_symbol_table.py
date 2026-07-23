"""
tests/test_symbol_table.py
---------------------------
Unit tests for Symbol models and SymbolTable core data structure.
"""

import pytest
from models.symbol import (
    Symbol,
    SymbolKind,
    SymbolLocation,
    SymbolMetrics,
    SymbolScope,
    SymbolVisibility,
    generate_symbol_id,
)
from analysis.symbol_table.symbol_table import SymbolTable
from models.ast import NodeLocation, NodeRange


def make_range(start_line: int, end_line: int) -> NodeRange:
    return NodeRange(
        start=NodeLocation(line=start_line, column=0),
        end=NodeLocation(line=end_line, column=10),
        start_byte=0,
        end_byte=100,
    )


class TestSymbolModels:
    def test_generate_symbol_id_deterministic(self):
        id1 = generate_symbol_id("repo1", "app.auth.login", SymbolKind.FUNCTION)
        id2 = generate_symbol_id("repo1", "app.auth.login", SymbolKind.FUNCTION)
        assert id1 == id2
        assert id1.startswith("sym-")

    def test_generate_symbol_id_different_for_different_inputs(self):
        id1 = generate_symbol_id("repo1", "app.auth.login", SymbolKind.FUNCTION)
        id2 = generate_symbol_id("repo1", "app.auth.login", SymbolKind.METHOD)
        id3 = generate_symbol_id("repo2", "app.auth.login", SymbolKind.FUNCTION)
        assert id1 != id2
        assert id1 != id3

    def test_symbol_defaults(self):
        sym = Symbol(
            id="sym-123",
            fqn="app.models.User",
            name="User",
            kind=SymbolKind.CLASS,
            file_path="app/models.py",
        )
        assert sym.scope == SymbolScope.GLOBAL
        assert sym.visibility == SymbolVisibility.PUBLIC
        assert sym.children_ids == []
        assert sym.parent_id is None


class TestSymbolTableOperations:
    def test_add_symbol_and_retrieval(self):
        table = SymbolTable(repository_id="repo1")
        sym = Symbol(
            id="sym-mod",
            fqn="app.auth",
            name="auth",
            kind=SymbolKind.MODULE,
            file_path="app/auth.py",
        )
        table.add_symbol(sym)
        assert len(table) == 1
        assert "sym-mod" in table
        assert table.get_symbol("sym-mod") == sym
        assert table.root_symbol_ids == ["sym-mod"]

    def test_freeze_prevents_mutation(self):
        table = SymbolTable()
        sym = Symbol(
            id="sym-1",
            fqn="m",
            name="m",
            kind=SymbolKind.MODULE,
            file_path="m.py",
        )
        table.add_symbol(sym)
        table.freeze()
        assert table.is_frozen is True

        with pytest.raises(RuntimeError, match="Cannot modify a frozen SymbolTable"):
            table.add_symbol(
                Symbol(
                    id="sym-2",
                    fqn="m2",
                    name="m2",
                    kind=SymbolKind.MODULE,
                    file_path="m2.py",
                )
            )

    def test_parent_child_wiring(self):
        table = SymbolTable()
        parent = Symbol(
            id="sym-parent",
            fqn="app.AuthService",
            name="AuthService",
            kind=SymbolKind.CLASS,
            file_path="app.py",
        )
        child = Symbol(
            id="sym-child",
            fqn="app.AuthService.login",
            name="login",
            kind=SymbolKind.METHOD,
            parent_id="sym-parent",
            file_path="app.py",
        )
        table.add_symbol(parent)
        table.add_symbol(child)

        assert "sym-child" in parent.children_ids
        assert table.get_parent("sym-child") == parent
        children = table.get_children("sym-parent")
        assert len(children) == 1
        assert children[0] == child

    def test_ancestors_traversal(self):
        table = SymbolTable()
        mod = Symbol(id="s-mod", fqn="app", name="app", kind=SymbolKind.MODULE, file_path="app.py")
        cls = Symbol(id="s-cls", fqn="app.User", name="User", kind=SymbolKind.CLASS, parent_id="s-mod", file_path="app.py")
        mth = Symbol(id="s-mth", fqn="app.User.save", name="save", kind=SymbolKind.METHOD, parent_id="s-cls", file_path="app.py")
        prm = Symbol(id="s-prm", fqn="app.User.save.force", name="force", kind=SymbolKind.PARAMETER, parent_id="s-mth", file_path="app.py")

        table.add_symbol(mod)
        table.add_symbol(cls)
        table.add_symbol(mth)
        table.add_symbol(prm)

        ancestors = table.get_ancestors("s-prm")
        anc_ids = [a.id for a in ancestors]
        assert anc_ids == ["s-mth", "s-cls", "s-mod"]

    def test_descendants_traversal(self):
        table = SymbolTable()
        mod = Symbol(id="s-mod", fqn="app", name="app", kind=SymbolKind.MODULE, file_path="app.py")
        cls = Symbol(id="s-cls", fqn="app.User", name="User", kind=SymbolKind.CLASS, parent_id="s-mod", file_path="app.py")
        mth = Symbol(id="s-mth", fqn="app.User.save", name="save", kind=SymbolKind.METHOD, parent_id="s-cls", file_path="app.py")

        table.add_symbol(mod)
        table.add_symbol(cls)
        table.add_symbol(mth)

        descendants = table.get_descendants("s-mod")
        desc_ids = [d.id for d in descendants]
        assert "s-cls" in desc_ids
        assert "s-mth" in desc_ids
