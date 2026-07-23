"""
tests/test_scope_validator.py
------------------------------
Unit tests for ScopeValidator graph integrity validator.
"""

from models.ast import NodeLocation, NodeRange
from models.scope import Scope, ScopeKind, ScopeLocation
from models.symbol import Symbol, SymbolKind
from analysis.scope_resolution.scope_tree import ScopeTree
from analysis.symbol_table.symbol_table import SymbolTable
from analysis.scope_resolution.scope_validator import ScopeValidator


class TestScopeValidator:
    def test_clean_scope_tree_is_valid(self):
        symbol_table = SymbolTable()
        mod_scope = Scope(id="s-mod", name="module:app", kind=ScopeKind.MODULE)
        tree = ScopeTree()
        tree.add_scope(mod_scope)

        validator = ScopeValidator()
        report = validator.validate(tree, symbol_table)

        assert report.is_valid is True
        assert report.error_count == 0

    def test_detect_dangling_parent_scope(self):
        symbol_table = SymbolTable()
        tree = ScopeTree()
        scope = Scope(id="s-func", name="func:test", kind=ScopeKind.FUNCTION, parent_id="non-existent-scope-id")
        tree.add_scope(scope)

        validator = ScopeValidator()
        report = validator.validate(tree, symbol_table)

        assert report.is_valid is False
        assert report.error_count == 1
        assert report.issues[0].code == "DANGLING_PARENT"

    def test_detect_unowned_symbol(self):
        symbol_table = SymbolTable()  # Empty symbol_table
        tree = ScopeTree()
        scope = Scope(id="s-mod", name="module:app", kind=ScopeKind.MODULE, defined_symbol_ids=["non-existent-sym-id"])
        tree.add_scope(scope)

        validator = ScopeValidator()
        report = validator.validate(tree, symbol_table)

        assert report.is_valid is False
        assert report.error_count == 1
        assert report.issues[0].code == "UNOWNED_SYMBOL"

    def test_detect_circular_parent_scopes(self):
        symbol_table = SymbolTable()
        tree = ScopeTree()
        s1 = Scope(id="s1", name="s1", kind=ScopeKind.CLASS, parent_id="s2")
        s2 = Scope(id="s2", name="s2", kind=ScopeKind.CLASS, parent_id="s1")

        tree.add_scope(s1)
        tree.add_scope(s2)

        validator = ScopeValidator()
        report = validator.validate(tree, symbol_table)

        assert report.is_valid is False
        codes = [i.code for i in report.issues]
        assert "CIRCULAR_SCOPE" in codes

    def test_detect_invalid_location_range(self):
        symbol_table = SymbolTable()
        tree = ScopeTree()
        inv_range = NodeRange.model_construct(
            start=NodeLocation(line=20, column=0),
            end=NodeLocation(line=5, column=0),
            start_byte=200,
            end_byte=50,
        )
        inv_loc = ScopeLocation.model_construct(file_path="app.py", range=inv_range)
        scope = Scope(id="s-inv", name="inv", kind=ScopeKind.MODULE, location=inv_loc)
        tree.add_scope(scope)

        validator = ScopeValidator()
        report = validator.validate(tree, symbol_table)

        codes = [i.code for i in report.issues]
        assert "INVALID_LOCATION" in codes
