"""
tests/test_core_type_reference_edges.py
-----------------------------------------
Comprehensive unit test suite for Step 4.5 Type Reference Edge Builder.
"""

from typing import List
import pytest

from core.edges import EdgeKind
from core.symbol_builder import SemanticRepository, SymbolBuilder
from core.type_reference_edges import (
    TYPE_REFERENCE_EDGE_COLLECTION_VERSION,
    ExtractedTypeReferenceStatement,
    TypeReferenceEdgeBuilder,
    TypeReferenceExtractor,
    TypeReferenceResolver,
    dict_to_type_reference_collection,
    hash_type_reference_collection,
    json_to_type_reference_collection,
    type_reference_collection_to_dict,
    type_reference_collection_to_json,
)
from models.parser import ParserLanguage, ParserMetadata, ParserResult, ParserStatistics, ParserVersion


class TestTypeReferenceEdgeBuilderFacade:
    def create_sample_pipeline_repository(self) -> SemanticRepository:
        ast1 = {
            "type": "module",
            "name": "services",
            "children": [
                {
                    "type": "class_def",
                    "name": "User",
                    "range": {"start": {"line": 1, "column": 0}, "end": {"line": 5, "column": 0}}
                },
                {
                    "type": "func_def",
                    "name": "create_user",
                    "metadata": {
                        "parameters": [{"name": "user", "type": "User"}],
                        "return_type": "User"
                    },
                    "range": {"start": {"line": 7, "column": 0}, "end": {"line": 15, "column": 0}}
                }
            ]
        }

        pr1 = ParserResult(
            job_id="job-1",
            file_path="src/services.py",
            language=ParserLanguage.PYTHON,
            statistics=ParserStatistics(lines_parsed=15, node_count=5),
            metadata=ParserMetadata(parser_name="tree-sitter", language=ParserLanguage.PYTHON, version=ParserVersion(semver="1.0.0")),
            ast_root=ast1
        )

        class MockWorkspace:
            def __init__(self, pr_list):
                self.id = "repo-typeref-test"
                self.repository_id = "repo-typeref-test"
                self.parser_results = pr_list

        ws = MockWorkspace([pr1])
        return SymbolBuilder.build(
            workspace=ws,
            parser_results=[pr1],
            repository_id="repo-typeref-test"
        )

    def test_type_reference_extractor_discovers_statements(self):
        repo = self.create_sample_pipeline_repository()
        extractor = TypeReferenceExtractor()

        stmts = extractor.extract_type_references(repo)
        assert len(stmts) >= 1
        assert stmts[0].referenced_type_raw == "User"

    def test_type_reference_resolver(self):
        repo = self.create_sample_pipeline_repository()
        resolver = TypeReferenceResolver()

        func_syms = repo.symbol_table.get_by_name("create_user")
        assert len(func_syms) >= 1

        stmt = ExtractedTypeReferenceStatement(
            source_file_path="src/services.py",
            source_symbol_id=func_syms[0].id,
            referenced_type_raw="User",
            context="parameter",
            language=func_syms[0].language
        )

        res = resolver.resolve_type_symbol(stmt, repo)
        assert res.is_resolved
        assert res.confidence == 1.0

    def test_primitive_type_resolution(self):
        repo = self.create_sample_pipeline_repository()
        resolver = TypeReferenceResolver()

        func_syms = repo.symbol_table.get_by_name("create_user")

        stmt = ExtractedTypeReferenceStatement(
            source_file_path="src/services.py",
            source_symbol_id=func_syms[0].id,
            referenced_type_raw="str",
            context="parameter",
            language=func_syms[0].language
        )

        res = resolver.resolve_type_symbol(stmt, repo)
        assert not res.is_resolved
        assert res.is_primitive
        assert res.resolution_strategy == "primitive_type"

    def test_type_reference_edge_builder_end_to_end(self):
        repo = self.create_sample_pipeline_repository()
        builder = TypeReferenceEdgeBuilder()

        edge_coll = builder.build(repo)

        assert edge_coll.repository_id == "repo-typeref-test"
        assert len(edge_coll.edges) >= 1

        for edge in edge_coll.edges:
            assert edge.kind == EdgeKind.TYPE_REFERENCE
            assert edge.id.value.startswith("edge_")


class TestSerialization:
    def test_json_roundtrip(self):
        repo = TestTypeReferenceEdgeBuilderFacade().create_sample_pipeline_repository()
        builder = TypeReferenceEdgeBuilder()
        edge_coll = builder.build(repo)

        json_str = type_reference_collection_to_json(edge_coll, indent=True)
        assert "_schema_version" in json_str

        reconstructed = json_to_type_reference_collection(json_str, type(edge_coll))
        assert reconstructed.repository_id == edge_coll.repository_id
        assert len(reconstructed.edges) == len(edge_coll.edges)

    def test_dict_roundtrip(self):
        repo = TestTypeReferenceEdgeBuilderFacade().create_sample_pipeline_repository()
        builder = TypeReferenceEdgeBuilder()
        edge_coll = builder.build(repo)

        d = type_reference_collection_to_dict(edge_coll)
        reconstructed = dict_to_type_reference_collection(d, type(edge_coll))
        assert reconstructed == edge_coll

    def test_hash_type_reference_collection(self):
        repo = TestTypeReferenceEdgeBuilderFacade().create_sample_pipeline_repository()
        builder = TypeReferenceEdgeBuilder()
        edge_coll = builder.build(repo)

        h1 = hash_type_reference_collection(edge_coll)
        h2 = hash_type_reference_collection(edge_coll)
        assert h1 == h2
        assert len(h1) == 64
