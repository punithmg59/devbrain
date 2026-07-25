"""
core/facade/facade.py
---------------------
DependencyGraphFacade Main Public Entrypoint for Repository Analyzer V2.
"""

from __future__ import annotations

import time
from typing import Any, List, Optional, Union

from core.call_edges import CallEdgeBuilder
from core.dependency_graph import (
    DependencyGraph,
    DependencyGraphBuilder,
    json_to_dependency_graph,
)
from core.edges import Edge, EdgeID
from core.facade.exceptions import FacadePipelineError
from core.facade.models import RepositoryAnalysisResult
from core.graph_validation import (
    DependencyGraphValidationReport,
    DependencyGraphValidator,
)
from core.import_edges import ImportEdgeBuilder
from core.inheritance_edges import InheritanceEdgeBuilder
from core.symbol_builder import SemanticRepository, SymbolBuilder
from core.symbol_identity import CanonicalSymbol
from core.symbols import SymbolID
from core.type_reference_edges import TypeReferenceEdgeBuilder
from models.parser import ParserResult


class DependencyGraphFacade:
    """
    Main Public Facade Entrypoint for DevBrain Repository Analyzer V2.
    Orchestrates the entire end-to-end analysis pipeline and provides O(1) fast graph queries.
    """

    @classmethod
    def analyze_repository(
        cls,
        parser_results: List[ParserResult],
        repository_id: str,
        workspace: Optional[Any] = None
    ) -> RepositoryAnalysisResult:
        """
        Orchestrates the complete 7-stage Dependency Graph Analysis Pipeline.
        """
        start_time = time.perf_counter()
        try:
            # 1. Step 3.6 - Symbol Builder Facade -> SemanticRepository
            semantic_repo: SemanticRepository = SymbolBuilder.build(
                parser_results=parser_results,
                repository_id=repository_id,
                workspace=workspace
            )

            # 2. Step 4.2 - Import Edge Builder
            import_edges = ImportEdgeBuilder().build(semantic_repo)

            # 3. Step 4.3 - Call Edge Builder
            call_edges = CallEdgeBuilder().build(semantic_repo)

            # 4. Step 4.4 - Inheritance Edge Builder
            inheritance_edges = InheritanceEdgeBuilder().build(semantic_repo)

            # 5. Step 4.5 - Type Reference Edge Builder
            type_ref_edges = TypeReferenceEdgeBuilder().build(semantic_repo)

            # 6. Step 4.6 - Primary Dependency Graph Builder -> DependencyGraph
            graph: DependencyGraph = DependencyGraphBuilder().build(
                semantic_repository=semantic_repo,
                import_edges=import_edges,
                call_edges=call_edges,
                inheritance_edges=inheritance_edges,
                type_reference_edges=type_ref_edges
            )

            # 7. Step 4.7 - Dependency Graph Validation Framework -> Report
            validation_report: DependencyGraphValidationReport = DependencyGraphValidator.validate(graph)

            total_duration_ms = (time.perf_counter() - start_time) * 1000.0

            return RepositoryAnalysisResult(
                repository_id=repository_id,
                semantic_repository=semantic_repo,
                graph=graph,
                validation_report=validation_report,
                duration_ms=total_duration_ms
            )

        except Exception as e:
            raise FacadePipelineError(f"Failed during pipeline orchestration for repository '{repository_id}': {str(e)}") from e

    @classmethod
    def load_graph(cls, json_str: str) -> DependencyGraph:
        """Deserialize a JSON string into a DependencyGraph instance."""
        return json_to_dependency_graph(json_str, DependencyGraph)

    @classmethod
    def validate_graph(cls, graph: DependencyGraph) -> DependencyGraphValidationReport:
        """Validate a DependencyGraph using the Step 4.7 Validation Framework."""
        return DependencyGraphValidator.validate(graph)

    # Fast Query Methods delegating directly to DependencyGraph $O(1)$ indexes
    @classmethod
    def get_symbol(cls, graph: DependencyGraph, symbol_id: Union[SymbolID, str]) -> Optional[CanonicalSymbol]:
        """Fetch canonical symbol by SymbolID in O(1) time."""
        return graph.get_symbol(symbol_id)

    @classmethod
    def get_symbols(cls, graph: DependencyGraph) -> List[CanonicalSymbol]:
        """Fetch all canonical symbols in graph."""
        return list(graph.canonical_symbols.symbols)

    @classmethod
    def get_edge(cls, graph: DependencyGraph, edge_id: Union[EdgeID, str]) -> Optional[Edge]:
        """Fetch canonical edge by EdgeID in O(1) time."""
        return graph.get_edge(edge_id)

    @classmethod
    def get_edges(cls, graph: DependencyGraph) -> List[Edge]:
        """Fetch all relationship edges in graph."""
        return list(graph.edges)

    @classmethod
    def get_outgoing_edges(cls, graph: DependencyGraph, symbol_id: Union[SymbolID, str]) -> List[Edge]:
        """Fetch all outgoing edges for a given SymbolID in O(1) time."""
        return graph.get_outgoing_edges(symbol_id)

    @classmethod
    def get_incoming_edges(cls, graph: DependencyGraph, symbol_id: Union[SymbolID, str]) -> List[Edge]:
        """Fetch all incoming edges for a given SymbolID in O(1) time."""
        return graph.get_incoming_edges(symbol_id)

    @classmethod
    def get_file_symbols(cls, graph: DependencyGraph, file_path: str) -> List[CanonicalSymbol]:
        """Fetch all canonical symbols declared within a file in O(1) time."""
        return graph.get_file_nodes(file_path)

    @classmethod
    def get_file_edges(cls, graph: DependencyGraph, file_path: str) -> List[Edge]:
        """Fetch all relationship edges for a file in O(1) time."""
        edge_ids = graph.indexes.edges_by_file.get(file_path, [])
        return [graph.indexes.edges_by_id[eid] for eid in edge_ids if eid in graph.indexes.edges_by_id]
