"""
tests/test_core_facade.py
--------------------------
Comprehensive unit test suite for Step 4.8 DependencyGraph Facade.
"""

from typing import Any, List
import pytest
from pydantic import BaseModel

from core.edges import EdgeKind
from core.facade import (
    ANALYSIS_RESULT_VERSION,
    DependencyGraphFacade,
    RepositoryAnalysisResult,
    analysis_result_to_dict,
    analysis_result_to_json,
    dict_to_analysis_result,
    hash_analysis_result,
    json_to_analysis_result,
)
from models.parser import ParserLanguage, ParserMetadata, ParserResult, ParserStatistics, ParserVersion


class TestDependencyGraphFacade:
    def create_sample_parser_results(self) -> tuple[List[ParserResult], Any]:
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
                    "range": {"start": {"line": 7, "column": 0}, "end": {"line": 15, "column": 0}},
                    "children": [
                        {
                            "type": "func_def",
                            "name": "login",
                            "metadata": {"parameters": [{"name": "user", "type": "BaseUser"}]},
                            "range": {"start": {"line": 9, "column": 4}, "end": {"line": 14, "column": 4}}
                        }
                    ]
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

        class MockWorkspace(BaseModel):
            id: str = "repo-facade-test"
            repository_id: str = "repo-facade-test"
            parser_results: List[Any] = []

            model_config = {"arbitrary_types_allowed": True}

        ws = MockWorkspace(parser_results=[pr1])
        return [pr1], ws

    def test_analyze_repository_end_to_end(self):
        pr_list, ws = self.create_sample_parser_results()

        result = DependencyGraphFacade.analyze_repository(
            parser_results=pr_list,
            repository_id="repo-facade-test",
            workspace=ws
        )

        assert isinstance(result, RepositoryAnalysisResult)
        assert result.repository_id == "repo-facade-test"
        assert result.semantic_repository is not None
        assert result.graph is not None
        assert result.validation_report is not None
        assert result.validation_report.is_valid
        assert result.duration_ms > 0

    def test_facade_query_convenience_methods(self):
        pr_list, ws = self.create_sample_parser_results()
        result = DependencyGraphFacade.analyze_repository(
            parser_results=pr_list,
            repository_id="repo-facade-test",
            workspace=ws
        )
        graph = result.graph

        # get_symbols & get_symbol
        symbols = DependencyGraphFacade.get_symbols(graph)
        assert len(symbols) >= 3
        sym0 = symbols[0]

        fetched_sym = DependencyGraphFacade.get_symbol(graph, sym0.id)
        assert fetched_sym == sym0

        # get_edges & get_edge
        edges = DependencyGraphFacade.get_edges(graph)
        assert len(edges) >= 1
        edge0 = edges[0]

        fetched_edge = DependencyGraphFacade.get_edge(graph, edge0.id)
        assert fetched_edge == edge0

        # get_outgoing_edges & get_incoming_edges
        out_edges = DependencyGraphFacade.get_outgoing_edges(graph, edge0.source_symbol_id)
        assert len(out_edges) >= 1

        inc_edges = DependencyGraphFacade.get_incoming_edges(graph, edge0.target_symbol_id)
        assert len(inc_edges) >= 1

        # get_file_symbols & get_file_edges
        file_syms = DependencyGraphFacade.get_file_symbols(graph, "src/models.py")
        assert len(file_syms) >= 3

        file_edges = DependencyGraphFacade.get_file_edges(graph, "src/models.py")
        assert len(file_edges) >= 1

    def test_validate_graph_delegation(self):
        pr_list, ws = self.create_sample_parser_results()
        result = DependencyGraphFacade.analyze_repository(
            parser_results=pr_list,
            repository_id="repo-facade-test",
            workspace=ws
        )

        report = DependencyGraphFacade.validate_graph(result.graph)
        assert report.is_valid
        assert report.repository_id == "repo-facade-test"


class TestSerialization:
    def test_json_roundtrip(self):
        pr_list, ws = TestDependencyGraphFacade().create_sample_parser_results()
        result = DependencyGraphFacade.analyze_repository(
            parser_results=pr_list,
            repository_id="repo-facade-test",
            workspace=ws
        )

        json_str = analysis_result_to_json(result, indent=True)
        assert "_schema_version" in json_str

        reconstructed = json_to_analysis_result(json_str, type(result))
        assert reconstructed.repository_id == result.repository_id
        assert len(reconstructed.graph.edges) == len(result.graph.edges)

    def test_dict_roundtrip(self):
        pr_list, ws = TestDependencyGraphFacade().create_sample_parser_results()
        result = DependencyGraphFacade.analyze_repository(
            parser_results=pr_list,
            repository_id="repo-facade-test",
            workspace=ws
        )

        d = analysis_result_to_dict(result)
        reconstructed = dict_to_analysis_result(d, type(result))
        assert reconstructed.repository_id == result.repository_id
        assert len(reconstructed.graph.edges) == len(result.graph.edges)

    def test_hash_analysis_result(self):
        pr_list, ws = TestDependencyGraphFacade().create_sample_parser_results()
        result = DependencyGraphFacade.analyze_repository(
            parser_results=pr_list,
            repository_id="repo-facade-test",
            workspace=ws
        )

        h1 = hash_analysis_result(result)
        h2 = hash_analysis_result(result)
        assert h1 == h2
        assert len(h1) == 64
