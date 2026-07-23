"""
tests/test_import_linker.py
----------------------------
Unit tests for ImportLinker cross-file symbol binding and wildcard expansion.
"""

from models.symbol import Symbol, SymbolKind
from analysis.symbol_table.symbol_table import SymbolTable
from analysis.import_resolution.import_linker import ImportLinker


class TestImportLinker:
    def test_link_symbol_direct(self):
        symbol_table = SymbolTable()
        mod_sym = Symbol(id="sym-mod", fqn="app.auth", name="auth", kind=SymbolKind.MODULE, file_path="app/auth.py")
        cls_sym = Symbol(id="sym-cls", fqn="app.auth.AuthService", name="AuthService", kind=SymbolKind.CLASS, file_path="app/auth.py", parent_id="sym-mod")

        symbol_table.add_symbol(mod_sym)
        symbol_table.add_symbol(cls_sym)

        linker = ImportLinker()
        linked = linker.link_symbol("app.auth", "AuthService", symbol_table)

        assert linked == cls_sym

    def test_expand_wildcard_symbols(self):
        symbol_table = SymbolTable()
        mod_sym = Symbol(id="sym-mod", fqn="app.models", name="models", kind=SymbolKind.MODULE, file_path="app/models.py")
        u_sym = Symbol(id="sym-u", fqn="app.models.User", name="User", kind=SymbolKind.CLASS, file_path="app/models.py", parent_id="sym-mod")
        p_sym = Symbol(id="sym-p", fqn="app.models.Post", name="Post", kind=SymbolKind.CLASS, file_path="app/models.py", parent_id="sym-mod")
        priv_sym = Symbol(id="sym-priv", fqn="app.models._internal", name="_internal", kind=SymbolKind.FUNCTION, file_path="app/models.py", parent_id="sym-mod")

        symbol_table.add_symbol(mod_sym)
        symbol_table.add_symbol(u_sym)
        symbol_table.add_symbol(p_sym)
        symbol_table.add_symbol(priv_sym)

        linker = ImportLinker()
        wildcard_syms = linker.expand_wildcard_symbols("app.models", symbol_table)

        sym_ids = [s.id for s in wildcard_syms]
        assert "sym-u" in sym_ids
        assert "sym-p" in sym_ids
        assert "sym-priv" not in sym_ids  # Excluded private underscore symbol
