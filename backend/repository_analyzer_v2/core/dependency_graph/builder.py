"""
core/dependency_graph/builder.py
---------------------------------
DependencyGraphBuilder Facade Entrypoint for assembling unified DependencyGraph.
"""

from __future__ import annotations

import time
from typing import Dict, List, Set

from core.dependency_graph.diagnostics import DependencyGraphDiagnostics, GraphDiagnostic
from core.dependency_graph.graph import DependencyGraph
from core.dependency_graph.indexes import DependencyGraphIndexes
from core.dependency_graph.statistics import DependencyGraphStatistics
from core.dependency_graph.validator import DependencyGraphValidator
from core.edges import Edge, EdgeCollection, EdgeID
from core.symbol_builder import SemanticRepository
from core.symbol_identity import CanonicalSymbol


class DependencyGraphBuilder:
    """
    Facade Entrypoint that merges EdgeCollections and SemanticRepository into an immutable DependencyGraph.
    """

    def build(
        self,
        semantic_repository: SemanticRepository,
        import_edges: EdgeCollection,
        call_edges: EdgeCollection,
        inheritance_edges: EdgeCollection,
        type_reference_edges: EdgeCollection
    ) -> DependencyGraph:
        start_time = time.perf_counter()
        repository_id = semantic_repository.repository_id

        # 1. Merge and Deduplicate Edges across all four EdgeCollections
        seen_edge_ids: Set[EdgeID] = set()
        merged_edges: List[Edge] = []

        all_collections = [import_edges, call_edges, inheritance_edges, type_reference_edges]
        for coll in all_collections:
            for edge in coll.edges:
                if edge.id not in seen_edge_ids:
                    seen_edge_ids.add(edge.id)
                    merged_edges.append(edge)

        # 2. Build Multi-Dimensional Indexes using String Keys
        nodes_by_id: Dict[str, CanonicalSymbol] = {}
        nodes_by_kind: Dict[str, List[str]] = {}
        nodes_by_file: Dict[str, List[str]] = {}
        nodes_by_language: Dict[str, List[str]] = {}

        for sym in semantic_repository.canonical_symbols.symbols:
            sid_str = sym.id.value
            kind_str = sym.kind.value
            lang_str = sym.language.value

            nodes_by_id[sid_str] = sym
            nodes_by_kind.setdefault(kind_str, []).append(sid_str)
            nodes_by_file.setdefault(sym.file_path, []).append(sid_str)
            nodes_by_language.setdefault(lang_str, []).append(sid_str)

        edges_by_id: Dict[str, Edge] = {}
        outgoing_edges: Dict[str, List[str]] = {}
        incoming_edges: Dict[str, List[str]] = {}
        edges_by_kind: Dict[str, List[str]] = {}
        edges_by_file: Dict[str, List[str]] = {}

        edges_by_kind_counts: Dict[str, int] = {}

        for edge in merged_edges:
            eid_str = edge.id.value
            src_str = edge.source_symbol_id.value
            tgt_str = edge.target_symbol_id.value
            edge_kind_str = edge.kind.value

            edges_by_id[eid_str] = edge
            outgoing_edges.setdefault(src_str, []).append(eid_str)
            incoming_edges.setdefault(tgt_str, []).append(eid_str)
            edges_by_kind.setdefault(edge_kind_str, []).append(eid_str)
            edges_by_file.setdefault(edge.file_path, []).append(eid_str)

            edges_by_kind_counts[edge_kind_str] = edges_by_kind_counts.get(edge_kind_str, 0) + 1

        indexes = DependencyGraphIndexes(
            nodes_by_id=nodes_by_id,
            edges_by_id=edges_by_id,
            outgoing_edges=outgoing_edges,
            incoming_edges=incoming_edges,
            edges_by_kind=edges_by_kind,
            edges_by_file=edges_by_file,
            nodes_by_kind=nodes_by_kind,
            nodes_by_file=nodes_by_file,
            nodes_by_language=nodes_by_language
        )

        # 3. Calculate Graph Density & Statistics
        total_nodes = len(nodes_by_id)
        total_edges = len(merged_edges)

        density = 0.0
        if total_nodes > 1:
            density = total_edges / float(total_nodes * (total_nodes - 1))

        nodes_by_lang_counts = {lang_str: len(sids) for lang_str, sids in nodes_by_language.items()}
        nodes_by_kind_counts = {kind_str: len(sids) for kind_str, sids in nodes_by_kind.items()}

        stats = DependencyGraphStatistics(
            total_nodes=total_nodes,
            total_edges=total_edges,
            edges_by_kind_counts=edges_by_kind_counts,
            nodes_by_language_counts=nodes_by_lang_counts,
            nodes_by_kind_counts=nodes_by_kind_counts,
            graph_density=density,
            duration_ms=(time.perf_counter() - start_time) * 1000.0
        )

        # 4. Aggregate Diagnostics across all Builders
        raw_diags: List[GraphDiagnostic] = []
        for coll in all_collections:
            if hasattr(coll.diagnostics, "diagnostics"):
                for d in coll.diagnostics.diagnostics:
                    raw_diags.append(GraphDiagnostic(
                        message=d.message,
                        severity=d.severity,
                        file_path=d.file_path,
                        line=d.line,
                        column=d.column,
                        code=d.code
                    ))

        aggregated_diags = DependencyGraphDiagnostics(diagnostics=raw_diags)

        # 5. Construct Immutable DependencyGraph
        graph = DependencyGraph(
            repository_id=repository_id,
            canonical_symbols=semantic_repository.canonical_symbols,
            symbol_table=semantic_repository.symbol_table,
            edges=merged_edges,
            indexes=indexes,
            statistics=stats,
            diagnostics=aggregated_diags
        )

        # 6. Integrity Validation
        DependencyGraphValidator.validate(graph)

        return graph
