"""
tests/test_core_call_edges.py
------------------------------
Comprehensive unit test suite for Step 4.3 Call Edge Builder.
"""

from typing import List
import pytest

from core.call_edges import (
    CALL_EDGE_COLLECTION_VERSION,
    CallEdgeBuilder,
    CallExtractor,
    CallResolver,
    ExtractedCallStatement,
    call_collection_to_dict,
    call_collection_to_json,
    dict_to_call_collection,
    hash_call_collection,
    json_to_call_collection,
)
from core.edges import EdgeKind
from core.symbol_builder import SemanticRepository, SymbolBuilder
from models.parser import ParserLanguage, ParserMetadata, ParserResult, ParserStatistics, ParserVersion


class TestCallEdgeBuilderFacade:
    def create_sample_pipeline_repository(self) -> SemanticRepository:
        ast1 = {
            "type": "module",
            "name": "services",
            "children": [
                {
                    "type": "class_def",
                    "name": "UserService",
                    "range": {"start": {"line": 1, "column": 0}, "end": {"line": 15, "column": 0}},
                    "children": [
                        {
                            "type": "func_def",
                            "name": "login",
                            "range": {"start": {"line": 3, "column": 4}, "end": {"line": 8, "column": 4}},
                            "children": [
                                {
                                    "type": "call_expression",
                                    "function": "self.save",
                                    "range": {"start": {"line": 5, "column": 8}, "end": {"line": 5, "column": 20}}
                                }
                            ]
                        },
                        {
                            "type": "func_def",
                            "name": "save",
                            "range": {"start": {"line": 10, "column": 4}, "end": {"line": 14, "column": 4}}
                        }
                    ]
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
                self.id = "repo-call-test"
                self.repository_id = "repo-call-test"
                self.parser_results = pr_list

        ws = MockWorkspace([pr1])
        return SymbolBuilder.build(
            workspace=ws,
            parser_results=[pr1],
            repository_id="repo-call-test"
        )

    def test_call_extractor_discovers_statements(self):
        repo = self.create_sample_pipeline_repository()
        extractor = CallExtractor()

        calls = extractor.extract_calls(repo)
        assert len(calls) >= 1
        assert calls[0].callee_name == "save"

    def test_call_resolver(self):
        repo = self.create_sample_pipeline_repository()
        resolver = CallResolver()

        login_syms = repo.symbol_table.get_by_name("login")
        assert len(login_syms) >= 1

        stmt = ExtractedCallStatement(
            source_file_path="src/services.py",
            caller_symbol_id=login_syms[0].id,
            callee_expression_raw="self.save",
            callee_name="save",
            receiver_expression="self",
            language=login_syms[0].language
        )

        res = resolver.resolve_callee(stmt, repo)
        assert res.is_resolved
        assert res.confidence >= 0.95

    def test_call_edge_builder_end_to_end(self):
        repo = self.create_sample_pipeline_repository()
        builder = CallEdgeBuilder()

        edge_coll = builder.build(repo)

        assert edge_coll.repository_id == "repo-call-test"
        assert len(edge_coll.edges) >= 1

        for edge in edge_coll.edges:
            assert edge.kind == EdgeKind.CALL
            assert edge.id.value.startswith("edge_")


class TestSerialization:
    def test_json_roundtrip(self):
        repo = TestCallEdgeBuilderFacade().create_sample_pipeline_repository()
        builder = CallEdgeBuilder()
        edge_coll = builder.build(repo)

        json_str = call_collection_to_json(edge_coll, indent=True)
        assert "_schema_version" in json_str

        reconstructed = json_to_call_collection(json_str, type(edge_coll))
        assert reconstructed.repository_id == edge_coll.repository_id
        assert len(reconstructed.edges) == len(edge_coll.edges)

    def test_dict_roundtrip(self):
        repo = TestCallEdgeBuilderFacade().create_sample_pipeline_repository()
        builder = CallEdgeBuilder()
        edge_coll = builder.build(repo)

        d = call_collection_to_dict(edge_coll)
        reconstructed = dict_to_call_collection(d, type(edge_coll))
        assert reconstructed == edge_coll

    def test_hash_call_collection(self):
        repo = TestCallEdgeBuilderFacade().create_sample_pipeline_repository()
        builder = CallEdgeBuilder()
        edge_coll = builder.build(repo)

        h1 = hash_call_collection(edge_coll)
        h2 = hash_call_collection(edge_coll)
        assert h1 == h2
        assert len(h1) == 64
