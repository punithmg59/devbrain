"""
tests/test_core_graph_validation.py
------------------------------------
Comprehensive unit test suite for Step 4.7 Dependency Graph Validation Framework.
"""

from typing import List
import pytest

from core.call_edges import CallEdgeBuilder
from core.dependency_graph import DependencyGraph, DependencyGraphBuilder
from core.graph_validation import (
    VALIDATION_REPORT_VERSION,
    DependencyGraphValidationReport,
    DependencyGraphValidator,
    dict_to_validation_report,
    hash_validation_report,
    json_to_validation_report,
    validation_report_to_dict,
    validation_report_to_json,
)
from core.import_edges import ImportEdgeBuilder
from core.inheritance_edges import InheritanceEdgeBuilder
from core.symbol_builder import SemanticRepository, SymbolBuilder
from core.type_reference_edges import TypeReferenceEdgeBuilder
from models.parser import ParserLanguage, ParserMetadata, ParserResult, ParserStatistics, ParserVersion


class TestDependencyGraphValidator:
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

        class MockWorkspace:
            def __init__(self, pr_list):
                self.id = "repo-validation-test"
                self.repository_id = "repo-validation-test"
                self.parser_results = pr_list

        ws = MockWorkspace([pr1])
        return SymbolBuilder.build(
            workspace=ws,
            parser_results=[pr1],
            repository_id="repo-validation-test"
        )

    def build_sample_graph(self) -> DependencyGraph:
        repo = self.create_sample_pipeline_repository()
        import_edges = ImportEdgeBuilder().build(repo)
        call_edges = CallEdgeBuilder().build(repo)
        inheritance_edges = InheritanceEdgeBuilder().build(repo)
        type_ref_edges = TypeReferenceEdgeBuilder().build(repo)

        return DependencyGraphBuilder().build(
            semantic_repository=repo,
            import_edges=import_edges,
            call_edges=call_edges,
            inheritance_edges=inheritance_edges,
            type_reference_edges=type_ref_edges
        )

    def test_validate_clean_graph(self):
        graph = self.build_sample_graph()
        report = DependencyGraphValidator.validate(graph)

        assert report.is_valid
        assert report.repository_id == "repo-validation-test"
        assert len(report.validated_graph_hash) == 64
        assert report.total_nodes_validated >= 3
        assert report.total_edges_validated >= 1
        assert "PASSED" in report.summary

    def test_validation_statistics_and_categories(self):
        graph = self.build_sample_graph()
        report = DependencyGraphValidator.validate(graph)

        assert report.statistics.rules_evaluated_count > 0
        assert report.statistics.total_nodes_validated == report.total_nodes_validated
        assert report.statistics.total_edges_validated == report.total_edges_validated


class TestSerialization:
    def test_json_roundtrip(self):
        graph = TestDependencyGraphValidator().build_sample_graph()
        report = DependencyGraphValidator.validate(graph)

        json_str = validation_report_to_json(report, indent=True)
        assert "_schema_version" in json_str

        reconstructed = json_to_validation_report(json_str, type(report))
        assert reconstructed.repository_id == report.repository_id
        assert reconstructed.is_valid == report.is_valid
        assert reconstructed.validated_graph_hash == report.validated_graph_hash

    def test_dict_roundtrip(self):
        graph = TestDependencyGraphValidator().build_sample_graph()
        report = DependencyGraphValidator.validate(graph)

        d = validation_report_to_dict(report)
        reconstructed = dict_to_validation_report(d, type(report))
        assert reconstructed == report

    def test_hash_validation_report(self):
        graph = TestDependencyGraphValidator().build_sample_graph()
        report = DependencyGraphValidator.validate(graph)

        h1 = hash_validation_report(report)
        h2 = hash_validation_report(report)
        assert h1 == h2
        assert len(h1) == 64
