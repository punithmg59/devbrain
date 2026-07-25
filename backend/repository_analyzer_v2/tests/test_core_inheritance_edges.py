"""
tests/test_core_inheritance_edges.py
------------------------------------
Comprehensive unit test suite for Step 4.4 Inheritance Edge Builder.
"""

from typing import List
import pytest

from core.edges import EdgeKind
from core.inheritance_edges import (
    INHERITANCE_EDGE_COLLECTION_VERSION,
    ExtractedInheritanceStatement,
    InheritanceEdgeBuilder,
    InheritanceExtractor,
    InheritanceResolver,
    dict_to_inheritance_collection,
    hash_inheritance_collection,
    inheritance_collection_to_dict,
    inheritance_collection_to_json,
    json_to_inheritance_collection,
)
from core.symbol_builder import SemanticRepository, SymbolBuilder
from models.parser import ParserLanguage, ParserMetadata, ParserResult, ParserStatistics, ParserVersion


class TestInheritanceEdgeBuilderFacade:
    def create_sample_pipeline_repository(self) -> SemanticRepository:
        ast1 = {
            "type": "module",
            "name": "models",
            "children": [
                {
                    "type": "class_def",
                    "name": "BaseUser",
                    "range": {"start": {"line": 1, "column": 0}, "end": {"line": 5, "column": 0}}
                },
                {
                    "type": "class_def",
                    "name": "AdminUser",
                    "superclasses": ["BaseUser"],
                    "range": {"start": {"line": 7, "column": 0}, "end": {"line": 15, "column": 0}}
                }
            ]
        }

        pr1 = ParserResult(
            job_id="job-1",
            file_path="src/models.py",
            language=ParserLanguage.PYTHON,
            statistics=ParserStatistics(lines_parsed=15, node_count=5),
            metadata=ParserMetadata(parser_name="tree-sitter", language=ParserLanguage.PYTHON, version=ParserVersion(semver="1.0.0")),
            ast_root=ast1
        )

        class MockWorkspace:
            def __init__(self, pr_list):
                self.id = "repo-inheritance-test"
                self.repository_id = "repo-inheritance-test"
                self.parser_results = pr_list

        ws = MockWorkspace([pr1])
        return SymbolBuilder.build(
            workspace=ws,
            parser_results=[pr1],
            repository_id="repo-inheritance-test"
        )

    def test_inheritance_extractor_discovers_statements(self):
        repo = self.create_sample_pipeline_repository()
        extractor = InheritanceExtractor()

        stmts = extractor.extract_inheritance(repo)
        assert len(stmts) >= 1
        assert stmts[0].base_type_raw == "BaseUser"

    def test_inheritance_resolver(self):
        repo = self.create_sample_pipeline_repository()
        resolver = InheritanceResolver()

        admin_syms = repo.symbol_table.get_by_name("AdminUser")
        assert len(admin_syms) >= 1

        stmt = ExtractedInheritanceStatement(
            source_file_path="src/models.py",
            derived_symbol_id=admin_syms[0].id,
            base_type_raw="BaseUser",
            language=admin_syms[0].language
        )

        res = resolver.resolve_base_type(stmt, repo)
        assert res.is_resolved
        assert res.confidence == 1.0

    def test_inheritance_edge_builder_end_to_end(self):
        repo = self.create_sample_pipeline_repository()
        builder = InheritanceEdgeBuilder()

        edge_coll = builder.build(repo)

        assert edge_coll.repository_id == "repo-inheritance-test"
        assert len(edge_coll.edges) >= 1

        for edge in edge_coll.edges:
            assert edge.kind in (EdgeKind.INHERITANCE, EdgeKind.IMPLEMENTATION)
            assert edge.id.value.startswith("edge_")


class TestSerialization:
    def test_json_roundtrip(self):
        repo = TestInheritanceEdgeBuilderFacade().create_sample_pipeline_repository()
        builder = InheritanceEdgeBuilder()
        edge_coll = builder.build(repo)

        json_str = inheritance_collection_to_json(edge_coll, indent=True)
        assert "_schema_version" in json_str

        reconstructed = json_to_inheritance_collection(json_str, type(edge_coll))
        assert reconstructed.repository_id == edge_coll.repository_id
        assert len(reconstructed.edges) == len(edge_coll.edges)

    def test_dict_roundtrip(self):
        repo = TestInheritanceEdgeBuilderFacade().create_sample_pipeline_repository()
        builder = InheritanceEdgeBuilder()
        edge_coll = builder.build(repo)

        d = inheritance_collection_to_dict(edge_coll)
        reconstructed = dict_to_inheritance_collection(d, type(edge_coll))
        assert reconstructed == edge_coll

    def test_hash_inheritance_collection(self):
        repo = TestInheritanceEdgeBuilderFacade().create_sample_pipeline_repository()
        builder = InheritanceEdgeBuilder()
        edge_coll = builder.build(repo)

        h1 = hash_inheritance_collection(edge_coll)
        h2 = hash_inheritance_collection(edge_coll)
        assert h1 == h2
        assert len(h1) == 64
