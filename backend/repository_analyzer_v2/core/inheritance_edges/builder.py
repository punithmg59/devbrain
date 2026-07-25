"""
core/inheritance_edges/builder.py
----------------------------------
InheritanceEdgeBuilder Facade Entrypoint for discovering and constructing Inheritance and Implementation Edges.
"""

from __future__ import annotations

import time
from typing import Dict, List

from core.edges import (
    Edge,
    EdgeAttributes,
    EdgeCollection,
    EdgeDirection,
    EdgeEvidence,
    EdgeID,
    EdgeKind,
    EdgeMetadata,
    EdgeOrigin,
    EdgeStatistics,
    EdgeStrength,
    EdgeVersion,
    generate_edge_id,
)
from core.edges.diagnostics import EdgeDiagnostic, EdgeDiagnostics
from core.inheritance_edges.diagnostics import InheritanceEdgeDiagnostics
from core.inheritance_edges.extractor import InheritanceExtractor
from core.inheritance_edges.resolver import InheritanceResolver
from core.inheritance_edges.statistics import InheritanceEdgeStatistics
from core.inheritance_edges.validator import InheritanceEdgeValidator
from core.symbol_builder import SemanticRepository
from core.symbols import SymbolID


class InheritanceEdgeBuilder:
    """
    Facade Entrypoint that converts SemanticRepository inheritance declarations into an immutable EdgeCollection.
    """

    def build(self, semantic_repository: SemanticRepository) -> EdgeCollection:
        start_time = time.perf_counter()
        repository_id = semantic_repository.repository_id
        diagnostics = InheritanceEdgeDiagnostics()

        extractor = InheritanceExtractor()
        resolver = InheritanceResolver()

        extracted_stmts = extractor.extract_inheritance(semantic_repository)

        edge_list: List[Edge] = []
        by_id: Dict[EdgeID, Edge] = {}
        by_src: Dict[SymbolID, List[EdgeID]] = {}
        by_tgt: Dict[SymbolID, List[EdgeID]] = {}
        by_kind: Dict[EdgeKind, List[EdgeID]] = {}

        resolved_count = 0
        unresolved_count = 0
        internal_count = 0
        external_count = 0
        iface_count = 0
        trait_count = 0
        per_lang_counts: Dict[str, int] = {}

        for idx, stmt in enumerate(extracted_stmts):
            try:
                res = resolver.resolve_base_type(stmt, semantic_repository)

                if res.is_resolved:
                    resolved_count += 1
                    internal_count += 1
                else:
                    unresolved_count += 1
                    external_count += 1
                    diagnostics = diagnostics.add_warning(
                        message=f"Unresolved base type '{stmt.base_type_raw}' for symbol in '{stmt.source_file_path}'.",
                        file_path=stmt.source_file_path,
                        code="WARN_UNRESOLVED_BASE_TYPE"
                    )

                if res.is_interface:
                    iface_count += 1
                if stmt.is_trait:
                    trait_count += 1

                edge_kind = EdgeKind.IMPLEMENTATION if res.is_interface else EdgeKind.INHERITANCE

                disc = f"inheritance_{idx}_{stmt.base_type_raw}"
                eid = generate_edge_id(
                    repository_id=repository_id,
                    source_symbol_id=stmt.derived_symbol_id,
                    target_symbol_id=res.target_symbol_id,
                    kind=edge_kind,
                    discriminator=disc
                )

                ev = EdgeEvidence(
                    file_path=stmt.source_file_path,
                    source_range=stmt.source_range,
                    ast_node_ref=stmt.ast_node_ref,
                    stage_name="Step 4.4 Inheritance Edge Builder",
                    builder_name="InheritanceEdgeBuilder",
                    confidence_source=res.resolution_strategy,
                    explanation=f"Inheritance relationship to '{stmt.base_type_raw}' resolved via '{res.resolution_strategy}'."
                )

                meta = EdgeMetadata(
                    language={"lang": stmt.language.value},
                    custom={
                        "base_type_raw": stmt.base_type_raw,
                        "is_interface": res.is_interface,
                        "is_trait": stmt.is_trait,
                        "is_mixin": stmt.is_mixin,
                        "resolved_fqn": res.resolved_fqn
                    }
                )

                edge = Edge(
                    id=eid,
                    source_symbol_id=stmt.derived_symbol_id,
                    target_symbol_id=res.target_symbol_id,
                    kind=edge_kind,
                    direction=EdgeDirection.DIRECTED,
                    strength=EdgeStrength.STRONG,
                    confidence=res.confidence,
                    language=stmt.language,
                    repository_id=repository_id,
                    file_path=stmt.source_file_path,
                    evidence=ev,
                    attributes=EdgeAttributes(),
                    origin=EdgeOrigin(creator="devbrain.inheritance_edge_builder", stage="Step 4.4"),
                    version=EdgeVersion(),
                    metadata=meta
                )

                edge_list.append(edge)
                by_id[edge.id] = edge
                by_src.setdefault(edge.source_symbol_id, []).append(edge.id)
                by_tgt.setdefault(edge.target_symbol_id, []).append(edge.id)
                by_kind.setdefault(edge_kind, []).append(edge.id)

                lang_str = stmt.language.value
                per_lang_counts[lang_str] = per_lang_counts.get(lang_str, 0) + 1

            except Exception as e:
                diagnostics = diagnostics.add_error(
                    message=f"Error constructing inheritance edge for base '{stmt.base_type_raw}': {str(e)}",
                    file_path=stmt.source_file_path,
                    code="ERR_INHERITANCE_EDGE_BUILD_FAILED"
                )

        coll_stats = EdgeStatistics(
            total_edges=len(edge_list),
            edges_by_kind_counts={
                "inheritance": len([e for e in edge_list if e.kind == EdgeKind.INHERITANCE]),
                "implementation": len([e for e in edge_list if e.kind == EdgeKind.IMPLEMENTATION])
            },
            duration_ms=(time.perf_counter() - start_time) * 1000.0
        )

        edge_diags = EdgeDiagnostics()
        if diagnostics.diagnostics:
            edge_diags = EdgeDiagnostics(diagnostics=[
                EdgeDiagnostic(
                    message=d.message,
                    severity=d.severity,
                    file_path=d.file_path,
                    line=d.line,
                    column=d.column,
                    code=d.code
                )
                for d in diagnostics.diagnostics
            ])

        collection = EdgeCollection(
            repository_id=repository_id,
            edges=edge_list,
            edges_by_id=by_id,
            edges_by_source=by_src,
            edges_by_target=by_tgt,
            edges_by_kind=by_kind,
            statistics=coll_stats,
            diagnostics=edge_diags
        )

        # Integrity Validation
        InheritanceEdgeValidator.validate(collection)

        return collection
