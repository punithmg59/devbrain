"""
tests/test_core_import_edges.py
--------------------------------
Comprehensive unit test suite for Step 4.2 Import Edge Builder.
"""

from typing import List
import pytest

from core.edges import EdgeKind
from core.import_edges import (
    IMPORT_EDGE_COLLECTION_VERSION,
    ExtractedImportStatement,
    ImportEdgeBuilder,
    ImportExtractor,
    ImportResolver,
    dict_to_import_collection,
    hash_import_collection,
    import_collection_to_dict,
    import_collection_to_json,
    json_to_import_collection,
)
from core.symbol_builder import SemanticRepository, SymbolBuilder
from models.parser import ParserLanguage, ParserMetadata, ParserResult, ParserStatistics, ParserVersion


class TestImportEdgeBuilderFacade:
    def create_sample_pipeline_repository(self) -> SemanticRepository:
        ast1 = {
            "type": "module",
            "name": "services",
            "children": [
                {
                    "type": "import_from_statement",
                    "module": "models",
                    "name": "UserModel",
                    "range": {"start": {"line": 1, "column": 0}, "end": {"line": 1, "column": 30}}
                },
                {
                    "type": "class_def",
                    "name": "UserService",
                    "range": {"start": {"line": 3, "column": 0}, "end": {"line": 15, "column": 0}},
                    "children": []
                }
            ]
        }

        pr1 = ParserResult(
            job_id="job-1",
            file_path="src/services.py",
            language=ParserLanguage.PYTHON,
            statistics=ParserStatistics(lines_parsed=15, node_count=4),
            metadata=ParserMetadata(parser_name="tree-sitter", language=ParserLanguage.PYTHON, version=ParserVersion(semver="1.0.0")),
            ast_root=ast1
        )

        ast2 = {
            "type": "module",
            "name": "models",
            "children": [
                {
                    "type": "class_def",
                    "name": "UserModel",
                    "range": {"start": {"line": 1, "column": 0}, "end": {"line": 10, "column": 0}},
                    "children": []
                }
            ]
        }

        pr2 = ParserResult(
            job_id="job-2",
            file_path="src/models.py",
            language=ParserLanguage.PYTHON,
            statistics=ParserStatistics(lines_parsed=10, node_count=2),
            metadata=ParserMetadata(parser_name="tree-sitter", language=ParserLanguage.PYTHON, version=ParserVersion(semver="1.0.0")),
            ast_root=ast2
        )

        return SymbolBuilder.build(
            parser_results=[pr1, pr2],
            repository_id="repo-import-test"
        )

    def test_import_extractor_discovers_statements(self):
        repo = self.create_sample_pipeline_repository()
        extractor = ImportExtractor()

        stmts = extractor.extract_imports(repo)
        assert len(stmts) >= 1
        assert stmts[0].imported_target_raw == "models" or "UserModel" in stmts[0].imported_target_raw

    def test_import_resolver(self):
        repo = self.create_sample_pipeline_repository()
        resolver = ImportResolver()

        file_syms = repo.get_symbols_in_file("src/services.py")
        assert len(file_syms) >= 1

        models_syms = repo.get_symbols_in_file("src/models.py")
        assert len(models_syms) >= 1
        target_fqn = models_syms[0].fqn.to_string()

        stmt = ExtractedImportStatement(
            source_file_path="src/services.py",
            source_symbol_id=file_syms[0].id,
            imported_target_raw=target_fqn,
            language=file_syms[0].language
        )

        res = resolver.resolve_import(stmt, repo)
        assert res.is_resolved
        assert res.confidence == 1.0

    def test_import_edge_builder_end_to_end(self):
        repo = self.create_sample_pipeline_repository()
        builder = ImportEdgeBuilder()

        edge_coll = builder.build(repo)

        assert edge_coll.repository_id == "repo-import-test"
        assert len(edge_coll.edges) >= 1

        # Verify all edges are EdgeKind.IMPORT
        for edge in edge_coll.edges:
            assert edge.kind == EdgeKind.IMPORT
            assert edge.id.value.startswith("edge_")


class TestSerialization:
    def test_json_roundtrip(self):
        repo = TestImportEdgeBuilderFacade().create_sample_pipeline_repository()
        builder = ImportEdgeBuilder()
        edge_coll = builder.build(repo)

        json_str = import_collection_to_json(edge_coll, indent=True)
        assert "_schema_version" in json_str

        reconstructed = json_to_import_collection(json_str, type(edge_coll))
        assert reconstructed.repository_id == edge_coll.repository_id
        assert len(reconstructed.edges) == len(edge_coll.edges)

    def test_dict_roundtrip(self):
        repo = TestImportEdgeBuilderFacade().create_sample_pipeline_repository()
        builder = ImportEdgeBuilder()
        edge_coll = builder.build(repo)

        d = import_collection_to_dict(edge_coll)
        reconstructed = dict_to_import_collection(d, type(edge_coll))
        assert reconstructed == edge_coll

    def test_hash_import_collection(self):
        repo = TestImportEdgeBuilderFacade().create_sample_pipeline_repository()
        builder = ImportEdgeBuilder()
        edge_coll = builder.build(repo)

        h1 = hash_import_collection(edge_coll)
        h2 = hash_import_collection(edge_coll)
        assert h1 == h2
        assert len(h1) == 64
