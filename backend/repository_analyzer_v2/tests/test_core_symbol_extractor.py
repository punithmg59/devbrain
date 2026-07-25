"""
tests/test_core_symbol_extractor.py
------------------------------------
Comprehensive unit test suite for Step 3.3 Symbol Extractor & RawSymbolCollection.
"""

from typing import Any
import pytest
from pydantic import ValidationError

from core.namespaces import NamespaceBuilder
from core.symbol_extractor import (
    PythonSymbolExtractor,
    RawSymbol,
    RawSymbolCollection,
    SymbolExtractionDiagnostics,
    SymbolExtractor,
    TemporaryExtractionID,
    collection_to_dict,
    collection_to_json,
    dict_to_collection,
    generate_temporary_id,
    hash_collection,
    json_to_collection,
)
from core.symbols import Language, NamespaceID, QualifiedName, SourceInformation, SourceLocation, SourceRange, SymbolKind, Visibility
from models.parser import ParserLanguage, ParserMetadata, ParserResult, ParserStatistics, ParserVersion


class TestRawSymbol:
    def test_raw_symbol_creation_and_fields(self):
        tmp_id = generate_temporary_id("repo-1", "app/main.py", "ns_123", "run", SymbolKind.FUNCTION)
        qname = QualifiedName.from_string("repo.app.main.run")

        sym = RawSymbol(
            temp_id=tmp_id,
            kind=SymbolKind.FUNCTION,
            name="run",
            qualified_name_candidate=qname,
            namespace_id=NamespaceID(value="ns_123"),
            language=Language.PYTHON,
            repository_id="repo-1",
            file_id="prs-1",
            file_path="app/main.py",
            parser_result_id="prs-1",
            source_info=SourceInformation(
                file_id="prs-1",
                file_path="app/main.py",
                range=SourceRange(start=SourceLocation(line=10, column=0), end=SourceLocation(line=15, column=0))
            )
        )

        assert sym.name == "run"
        assert sym.kind == SymbolKind.FUNCTION
        assert sym.language == Language.PYTHON
        assert sym.temp_id.value.startswith("tmp_sym_")

    def test_raw_symbol_immutability(self):
        tmp_id = generate_temporary_id("repo-1", "app/main.py", "ns_123", "run", SymbolKind.FUNCTION)
        qname = QualifiedName.from_string("repo.app.main.run")

        sym = RawSymbol(
            temp_id=tmp_id,
            kind=SymbolKind.FUNCTION,
            name="run",
            qualified_name_candidate=qname,
            namespace_id=NamespaceID(value="ns_123"),
            language=Language.PYTHON,
            repository_id="repo-1",
            file_id="prs-1",
            file_path="app/main.py",
            parser_result_id="prs-1",
            source_info=SourceInformation(
                file_id="prs-1",
                file_path="app/main.py",
                range=SourceRange(start=SourceLocation(line=10, column=0), end=SourceLocation(line=15, column=0))
            )
        )

        with pytest.raises(ValidationError):
            sym.name = "new_run"  # type: ignore


class TestPythonSymbolExtractor:
    def create_sample_parser_result_and_tree(self) -> tuple[ParserResult, Any]:
        ast_root = {
            "type": "module",
            "name": "service",
            "children": [
                {
                    "type": "class_definition",
                    "name": "AuthService",
                    "docstring": "Authentication Service Class",
                    "range": {"start": {"line": 2, "column": 0}, "end": {"line": 20, "column": 0}},
                    "children": [
                        {
                            "type": "async_function_definition",
                            "name": "login",
                            "docstring": "Login method",
                            "range": {"start": {"line": 5, "column": 4}, "end": {"line": 12, "column": 4}}
                        },
                        {
                            "type": "assign",
                            "name": "MAX_RETRIES",
                            "range": {"start": {"line": 14, "column": 4}, "end": {"line": 14, "column": 20}}
                        }
                    ]
                },
                {
                    "type": "import_from",
                    "name": "typing",
                    "range": {"start": {"line": 1, "column": 0}, "end": {"line": 1, "column": 20}}
                }
            ]
        }

        pr = ParserResult(
            job_id="job-1",
            file_path="src/service.py",
            language=ParserLanguage.PYTHON,
            statistics=ParserStatistics(lines_parsed=30, node_count=10),
            metadata=ParserMetadata(parser_name="tree-sitter", language=ParserLanguage.PYTHON, version=ParserVersion(semver="1.0.0")),
            ast_root=ast_root
        )

        tree_builder = NamespaceBuilder()
        tree = tree_builder.build_tree([pr], repository_id="repo-devbrain")
        return pr, tree

    def test_extract_symbols_from_python_ast(self):
        pr, tree = self.create_sample_parser_result_and_tree()
        extractor = PythonSymbolExtractor()

        symbols = extractor.extract(pr, tree, repository_id="repo-devbrain")
        assert len(symbols) >= 3

        # Check Class symbol
        class_sym = next(s for s in symbols if s.name == "AuthService")
        assert class_sym.kind == SymbolKind.CLASS
        assert class_sym.doc.summary == "Authentication Service Class"

        # Check Method symbol
        method_sym = next(s for s in symbols if s.name == "login")
        assert method_sym.kind == SymbolKind.METHOD
        assert method_sym.modifiers.is_async

        # Check Constant symbol
        const_sym = next(s for s in symbols if s.name == "MAX_RETRIES")
        assert const_sym.kind == SymbolKind.CONSTANT

    def test_symbol_extractor_facade_end_to_end(self):
        pr, tree = self.create_sample_parser_result_and_tree()
        facade = SymbolExtractor()

        collection = facade.extract_symbols([pr], tree)

        assert collection.repository_id == "repo-devbrain"
        assert len(collection.symbols) >= 3
        assert collection.statistics.total_symbols >= 3
        assert "class" in collection.statistics.symbols_by_kind

        # Lookup helpers
        sym_by_id = collection.get_symbol(collection.symbols[0].temp_id)
        assert sym_by_id is not None

        syms_by_file = collection.get_symbols_in_file("src/service.py")
        assert len(syms_by_file) == len(collection.symbols)


class TestSerialization:
    def test_json_roundtrip(self):
        pr, tree = TestPythonSymbolExtractor().create_sample_parser_result_and_tree()
        facade = SymbolExtractor()
        collection = facade.extract_symbols([pr], tree)

        json_str = collection_to_json(collection, indent=True)
        assert "_schema_version" in json_str

        reconstructed = json_to_collection(json_str, RawSymbolCollection)
        assert reconstructed.repository_id == collection.repository_id
        assert len(reconstructed.symbols) == len(collection.symbols)

    def test_dict_roundtrip(self):
        pr, tree = TestPythonSymbolExtractor().create_sample_parser_result_and_tree()
        facade = SymbolExtractor()
        collection = facade.extract_symbols([pr], tree)

        d = collection_to_dict(collection)
        reconstructed = dict_to_collection(d, RawSymbolCollection)
        assert reconstructed == collection

    def test_hash_collection(self):
        pr, tree = TestPythonSymbolExtractor().create_sample_parser_result_and_tree()
        facade = SymbolExtractor()
        collection = facade.extract_symbols([pr], tree)

        h1 = hash_collection(collection)
        h2 = hash_collection(collection)
        assert h1 == h2
        assert len(h1) == 64
