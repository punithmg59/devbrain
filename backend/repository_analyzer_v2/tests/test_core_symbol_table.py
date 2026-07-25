"""
tests/test_core_symbol_table.py
--------------------------------
Comprehensive unit test suite for Step 3.5 Symbol Table Builder & Immutable SymbolTable.
"""

from typing import Any
import pytest
from pydantic import ValidationError

from core.namespaces import NamespaceBuilder
from core.symbol_extractor import RawSymbol, RawSymbolCollection, generate_temporary_id
from core.symbol_identity import SymbolIdentityBuilder
from core.symbol_table import (
    SYMBOL_TABLE_VERSION,
    SymbolIndexSet,
    SymbolTable,
    SymbolTableBuilder,
    dict_to_table,
    hash_symbol_table,
    json_to_table,
    table_to_dict,
    table_to_json,
)
from core.symbols import (
    Language,
    NamespaceID,
    QualifiedName,
    SourceInformation,
    SourceLocation,
    SourceRange,
    SymbolID,
    SymbolKind,
    VisibilityKind,
)
from models.parser import ParserLanguage, ParserMetadata, ParserResult, ParserStatistics, ParserVersion


class TestSymbolTableQueries:
    def create_sample_pipeline_table(self) -> tuple[SymbolTable, Any]:
        ast_root = {
            "type": "module",
            "name": "service",
            "children": [
                {
                    "type": "class_def",
                    "name": "AuthService",
                    "range": {"start": {"line": 2, "column": 0}, "end": {"line": 15, "column": 0}},
                    "children": [
                        {
                            "type": "func_def",
                            "name": "login",
                            "range": {"start": {"line": 5, "column": 4}, "end": {"line": 10, "column": 4}}
                        }
                    ]
                }
            ]
        }

        pr = ParserResult(
            job_id="job-1",
            file_path="src/service.py",
            language=ParserLanguage.PYTHON,
            statistics=ParserStatistics(lines_parsed=20, node_count=5),
            metadata=ParserMetadata(parser_name="tree-sitter", language=ParserLanguage.PYTHON, version=ParserVersion(semver="1.0.0")),
            ast_root=ast_root
        )

        tree_builder = NamespaceBuilder()
        tree = tree_builder.build_tree([pr], repository_id="repo-devbrain")

        mod_node = tree.get_by_fqn("repo.src.service")
        assert mod_node is not None

        raw1 = RawSymbol(
            temp_id=generate_temporary_id("repo-devbrain", "src/service.py", mod_node.id, "AuthService", SymbolKind.CLASS, 1),
            kind=SymbolKind.CLASS,
            name="AuthService",
            qualified_name_candidate=mod_node.fqn.child("AuthService"),
            namespace_id=mod_node.id,
            language=Language.PYTHON,
            repository_id="repo-devbrain",
            file_id=pr.result_id,
            file_path="src/service.py",
            parser_result_id=pr.result_id,
            source_info=SourceInformation(
                file_id=pr.result_id,
                file_path="src/service.py",
                range=SourceRange(start=SourceLocation(line=2, column=0), end=SourceLocation(line=15, column=0))
            )
        )

        class_node = tree.get_by_fqn("repo.src.service.AuthService")
        assert class_node is not None

        raw2 = RawSymbol(
            temp_id=generate_temporary_id("repo-devbrain", "src/service.py", class_node.id, "login", SymbolKind.METHOD, 2),
            kind=SymbolKind.METHOD,
            name="login",
            qualified_name_candidate=class_node.fqn.child("login"),
            namespace_id=class_node.id,
            language=Language.PYTHON,
            repository_id="repo-devbrain",
            file_id=pr.result_id,
            file_path="src/service.py",
            parser_result_id=pr.result_id,
            source_info=SourceInformation(
                file_id=pr.result_id,
                file_path="src/service.py",
                range=SourceRange(start=SourceLocation(line=5, column=4), end=SourceLocation(line=10, column=4))
            )
        )

        raw_coll = RawSymbolCollection(
            repository_id="repo-devbrain",
            symbols=[raw1, raw2],
            symbols_by_file={"src/service.py": [raw1.temp_id, raw2.temp_id]}
        )

        identity_builder = SymbolIdentityBuilder()
        canonical_coll = identity_builder.build_canonical_symbols(raw_coll, tree)

        table_builder = SymbolTableBuilder()
        table = table_builder.build_symbol_table(canonical_coll, tree)

        return table, tree

    def test_o1_lookups_by_id_and_fqn(self):
        table, tree = self.create_sample_pipeline_table()

        # O(1) FQN lookup
        class_sym = table.get_by_qualified_name("repo.src.service.AuthService")
        assert class_sym is not None
        assert class_sym.name == "AuthService"
        assert class_sym.kind == SymbolKind.CLASS

        # O(1) SymbolID lookup
        sym_by_id = table.get_by_symbol_id(class_sym.id)
        assert sym_by_id is not None
        assert sym_by_id == class_sym

    def test_multi_index_queries(self):
        table, tree = self.create_sample_pipeline_table()

        # Simple name lookup
        login_syms = table.get_by_name("login")
        assert len(login_syms) == 1
        assert login_syms[0].kind == SymbolKind.METHOD

        # File symbols lookup
        file_syms = table.get_file_symbols("src/service.py")
        assert len(file_syms) == 2

        # Language symbols lookup
        py_syms = table.get_language_symbols(Language.PYTHON)
        assert len(py_syms) == 2

        # SymbolKind lookup
        method_syms = table.get_symbols_by_kind(SymbolKind.METHOD)
        assert len(method_syms) == 1
        assert method_syms[0].name == "login"

        # Visibility lookup
        pub_syms = table.get_visible_symbols(VisibilityKind.PUBLIC)
        assert len(pub_syms) == 2

    def test_query_helpers(self):
        table, tree = self.create_sample_pipeline_table()

        assert table.contains("repo.src.service.AuthService")
        assert table.exists("repo.src.service.AuthService.login")
        assert not table.exists("non.existent.FQN")

        assert table.count() == 2
        all_syms = list(table.iterate())
        assert len(all_syms) == 2

    def test_immutability(self):
        table, tree = self.create_sample_pipeline_table()
        with pytest.raises(ValidationError):
            table.repository_id = "new-repo"  # type: ignore


class TestSerialization:
    def test_json_roundtrip(self):
        table, tree = TestSymbolTableQueries().create_sample_pipeline_table()

        json_str = table_to_json(table, indent=True)
        assert "_schema_version" in json_str

        reconstructed = json_to_table(json_str, SymbolTable)
        assert reconstructed.repository_id == table.repository_id
        assert reconstructed.count() == table.count()

    def test_dict_roundtrip(self):
        table, tree = TestSymbolTableQueries().create_sample_pipeline_table()

        d = table_to_dict(table)
        reconstructed = dict_to_table(d, SymbolTable)
        assert reconstructed == table

    def test_hash_symbol_table(self):
        table, tree = TestSymbolTableQueries().create_sample_pipeline_table()

        h1 = hash_symbol_table(table)
        h2 = hash_symbol_table(table)
        assert h1 == h2
        assert len(h1) == 64
