"""
tests/test_core_dependency_graph.py
------------------------------------
Comprehensive unit test suite for Step 4.6 Primary Dependency Graph Builder.
"""

from typing import List
import pytest

from core.call_edges import CallEdgeBuilder
from core.dependency_graph import (
    DEPENDENCY_GRAPH_VERSION,
    DependencyGraph,
    DependencyGraphBuilder,
    dependency_graph_to_dict,
    dependency_graph_to_json,
    dict_to_dependency_graph,
    hash_dependency_graph,
    json_to_dependency_graph,
)
from core.edges import EdgeKind
from core.import_edges import ImportEdgeBuilder
from core.inheritance_edges import InheritanceEdgeBuilder
from core.symbol_builder import SemanticRepository, SymbolBuilder
from core.type_reference_edges import TypeReferenceEdgeBuilder
from models.parser import ParserLanguage, ParserMetadata, ParserResult, ParserStatistics, ParserVersion


class TestDependencyGraphBuilderFacade:
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
                self.id = "repo-depgraph-test"
                self.repository_id = "repo-depgraph-test"
                self.parser_results = pr_list

        ws = MockWorkspace([pr1])
        return SymbolBuilder.build(
            workspace=ws,
            parser_results=[pr1],
            repository_id="repo-depgraph-test"
        )

    def test_dependency_graph_builder_end_to_end(self):
        repo = self.create_sample_pipeline_repository()

        import_edges = ImportEdgeBuilder().build(repo)
        call_edges = CallEdgeBuilder().build(repo)
        inheritance_edges = InheritanceEdgeBuilder().build(repo)
        type_ref_edges = TypeReferenceEdgeBuilder().build(repo)

        graph = DependencyGraphBuilder().build(
            semantic_repository=repo,
            import_edges=import_edges,
            call_edges=call_edges,
            inheritance_edges=inheritance_edges,
            type_reference_edges=type_ref_edges
        )

        assert graph.repository_id == "repo-depgraph-test"
        assert len(graph.canonical_symbols.symbols) >= 3
        assert len(graph.edges) >= 1
        assert graph.version == DEPENDENCY_GRAPH_VERSION

    def test_dependency_graph_indexes_and_lookups(self):
        repo = self.create_sample_pipeline_repository()

        import_edges = ImportEdgeBuilder().build(repo)
        call_edges = CallEdgeBuilder().build(repo)
        inheritance_edges = InheritanceEdgeBuilder().build(repo)
        type_ref_edges = TypeReferenceEdgeBuilder().build(repo)

        graph = DependencyGraphBuilder().build(
            semantic_repository=repo,
            import_edges=import_edges,
            call_edges=call_edges,
            inheritance_edges=inheritance_edges,
            type_reference_edges=type_ref_edges
        )

        # Query nodes by file
        file_nodes = graph.get_file_nodes("src/models.py")
        assert len(file_nodes) >= 3

        # Query inheritance edges
        inh_edges = graph.get_edges_by_kind(EdgeKind.INHERITANCE)
        assert len(inh_edges) >= 1

        first_edge = inh_edges[0]
        # Query outgoing edges from child class
        out_edges = graph.get_outgoing_edges(first_edge.source_symbol_id)
        assert len(out_edges) >= 1


class TestSerialization:
    def test_json_roundtrip(self):
        repo = TestDependencyGraphBuilderFacade().create_sample_pipeline_repository()
        graph = DependencyGraphBuilder().build(
            semantic_repository=repo,
            import_edges=ImportEdgeBuilder().build(repo),
            call_edges=CallEdgeBuilder().build(repo),
            inheritance_edges=InheritanceEdgeBuilder().build(repo),
            type_reference_edges=TypeReferenceEdgeBuilder().build(repo)
        )

        json_str = dependency_graph_to_json(graph, indent=True)
        assert "_schema_version" in json_str

        reconstructed = json_to_dependency_graph(json_str, type(graph))
        assert reconstructed.repository_id == graph.repository_id
        assert len(reconstructed.edges) == len(graph.edges)

    def test_dict_roundtrip(self):
        repo = TestDependencyGraphBuilderFacade().create_sample_pipeline_repository()
        graph = DependencyGraphBuilder().build(
            semantic_repository=repo,
            import_edges=ImportEdgeBuilder().build(repo),
            call_edges=CallEdgeBuilder().build(repo),
            inheritance_edges=InheritanceEdgeBuilder().build(repo),
            type_reference_edges=TypeReferenceEdgeBuilder().build(repo)
        )

        d = dependency_graph_to_dict(graph)
        reconstructed = dict_to_dependency_graph(d, type(graph))
        assert reconstructed.repository_id == graph.repository_id
        assert len(reconstructed.edges) == len(graph.edges)

    def test_hash_dependency_graph(self):
        repo = TestDependencyGraphBuilderFacade().create_sample_pipeline_repository()
        graph = DependencyGraphBuilder().build(
            semantic_repository=repo,
            import_edges=ImportEdgeBuilder().build(repo),
            call_edges=CallEdgeBuilder().build(repo),
            inheritance_edges=InheritanceEdgeBuilder().build(repo),
            type_reference_edges=TypeReferenceEdgeBuilder().build(repo)
        )

        h1 = hash_dependency_graph(graph)
        h2 = hash_dependency_graph(graph)
        assert h1 == h2
        assert len(h1) == 64
