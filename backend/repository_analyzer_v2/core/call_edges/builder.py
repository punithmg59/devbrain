"""
core/call_edges/builder.py
---------------------------
CallEdgeBuilder Facade Entrypoint for discovering and constructing Call Edges.
"""

from __future__ import annotations

import time
from typing import Dict, List

from core.call_edges.diagnostics import CallEdgeDiagnostics
from core.call_edges.extractor import CallExtractor
from core.call_edges.resolver import CallResolver
from core.call_edges.statistics import CallEdgeStatistics
from core.call_edges.validator import CallEdgeValidator
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
from core.symbol_builder import SemanticRepository
from core.symbols import SymbolID


class CallEdgeBuilder:
    """
    Facade Entrypoint that converts SemanticRepository call expressions into an immutable EdgeCollection.
    """

    def build(self, semantic_repository: SemanticRepository) -> EdgeCollection:
        start_time = time.perf_counter()
        repository_id = semantic_repository.repository_id
        diagnostics = CallEdgeDiagnostics()

        extractor = CallExtractor()
        resolver = CallResolver()

        extracted_stmts = extractor.extract_calls(semantic_repository)

        edge_list: List[Edge] = []
        by_id: Dict[EdgeID, Edge] = {}
        by_src: Dict[SymbolID, List[EdgeID]] = {}
        by_tgt: Dict[SymbolID, List[EdgeID]] = {}
        by_kind: Dict[EdgeKind, List[EdgeID]] = {}

        resolved_count = 0
        unresolved_count = 0
        internal_count = 0
        external_count = 0
        recursive_count = 0
        per_lang_counts: Dict[str, int] = {}

        for idx, stmt in enumerate(extracted_stmts):
            try:
                res = resolver.resolve_callee(stmt, semantic_repository)

                if res.is_resolved:
                    resolved_count += 1
                    internal_count += 1
                else:
                    unresolved_count += 1
                    external_count += 1
                    diagnostics = diagnostics.add_warning(
                        message=f"Unresolved call expression '{stmt.callee_expression_raw}' in '{stmt.source_file_path}'.",
                        file_path=stmt.source_file_path,
                        code="WARN_UNRESOLVED_CALL"
                    )

                if res.is_recursive:
                    recursive_count += 1

                disc = f"call_{idx}_{stmt.callee_expression_raw}"
                eid = generate_edge_id(
                    repository_id=repository_id,
                    source_symbol_id=stmt.caller_symbol_id,
                    target_symbol_id=res.target_symbol_id,
                    kind=EdgeKind.CALL,
                    discriminator=disc
                )

                ev = EdgeEvidence(
                    file_path=stmt.source_file_path,
                    source_range=stmt.source_range,
                    ast_node_ref=stmt.ast_node_ref,
                    stage_name="Step 4.3 Call Edge Builder",
                    builder_name="CallEdgeBuilder",
                    confidence_source=res.resolution_strategy,
                    explanation=f"Call expression '{stmt.callee_expression_raw}' resolved via '{res.resolution_strategy}'."
                )

                meta = EdgeMetadata(
                    language={"lang": stmt.language.value},
                    custom={
                        "callee_expression_raw": stmt.callee_expression_raw,
                        "callee_name": stmt.callee_name,
                        "receiver_expression": stmt.receiver_expression,
                        "is_constructor": stmt.is_constructor,
                        "is_static": stmt.is_static,
                        "is_recursive": res.is_recursive,
                        "resolved_fqn": res.resolved_fqn
                    }
                )

                edge = Edge(
                    id=eid,
                    source_symbol_id=stmt.caller_symbol_id,
                    target_symbol_id=res.target_symbol_id,
                    kind=EdgeKind.CALL,
                    direction=EdgeDirection.DIRECTED,
                    strength=EdgeStrength.NORMAL,
                    confidence=res.confidence,
                    language=stmt.language,
                    repository_id=repository_id,
                    file_path=stmt.source_file_path,
                    evidence=ev,
                    attributes=EdgeAttributes(),
                    origin=EdgeOrigin(creator="devbrain.call_edge_builder", stage="Step 4.3"),
                    version=EdgeVersion(),
                    metadata=meta
                )

                edge_list.append(edge)
                by_id[edge.id] = edge
                by_src.setdefault(edge.source_symbol_id, []).append(edge.id)
                by_tgt.setdefault(edge.target_symbol_id, []).append(edge.id)
                by_kind.setdefault(EdgeKind.CALL, []).append(edge.id)

                lang_str = stmt.language.value
                per_lang_counts[lang_str] = per_lang_counts.get(lang_str, 0) + 1

            except Exception as e:
                diagnostics = diagnostics.add_error(
                    message=f"Error constructing call edge for expression '{stmt.callee_expression_raw}': {str(e)}",
                    file_path=stmt.source_file_path,
                    code="ERR_CALL_EDGE_BUILD_FAILED"
                )

        coll_stats = EdgeStatistics(
            total_edges=len(edge_list),
            edges_by_kind_counts={"call": len(edge_list)},
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
        CallEdgeValidator.validate(collection)

        return collection
