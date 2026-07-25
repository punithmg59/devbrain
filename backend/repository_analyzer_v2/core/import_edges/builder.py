"""
core/import_edges/builder.py
-----------------------------
ImportEdgeBuilder Facade Entrypoint for discovering and constructing Import Edges.
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
from core.import_edges.diagnostics import ImportEdgeDiagnostics
from core.import_edges.extractor import ImportExtractor
from core.import_edges.resolver import ImportResolver
from core.import_edges.statistics import ImportEdgeStatistics
from core.import_edges.validator import ImportEdgeValidator
from core.symbol_builder import SemanticRepository
from core.symbols import SymbolID


class ImportEdgeBuilder:
    """
    Facade Entrypoint that converts SemanticRepository import statements into an immutable EdgeCollection.
    """

    def build(self, semantic_repository: SemanticRepository) -> EdgeCollection:
        start_time = time.perf_counter()
        repository_id = semantic_repository.repository_id
        diagnostics = ImportEdgeDiagnostics()

        extractor = ImportExtractor()
        resolver = ImportResolver()

        extracted_stmts = extractor.extract_imports(semantic_repository)

        edge_list: List[Edge] = []
        by_id: Dict[EdgeID, Edge] = {}
        by_src: Dict[SymbolID, List[EdgeID]] = {}
        by_tgt: Dict[SymbolID, List[EdgeID]] = {}
        by_kind: Dict[EdgeKind, List[EdgeID]] = {}

        resolved_count = 0
        unresolved_count = 0
        internal_count = 0
        external_count = 0
        per_lang_counts: Dict[str, int] = {}

        for idx, stmt in enumerate(extracted_stmts):
            try:
                res = resolver.resolve_import(stmt, semantic_repository)

                if res.is_resolved:
                    resolved_count += 1
                    internal_count += 1
                else:
                    unresolved_count += 1
                    external_count += 1
                    diagnostics = diagnostics.add_warning(
                        message=f"Unresolved external import '{stmt.imported_target_raw}' in '{stmt.source_file_path}'.",
                        file_path=stmt.source_file_path,
                        code="WARN_UNRESOLVED_IMPORT"
                    )

                disc = f"import_{idx}_{stmt.imported_target_raw}"
                eid = generate_edge_id(
                    repository_id=repository_id,
                    source_symbol_id=stmt.source_symbol_id,
                    target_symbol_id=res.target_symbol_id,
                    kind=EdgeKind.IMPORT,
                    discriminator=disc
                )

                ev = EdgeEvidence(
                    file_path=stmt.source_file_path,
                    source_range=stmt.source_range,
                    ast_node_ref=stmt.ast_node_ref,
                    stage_name="Step 4.2 Import Edge Builder",
                    builder_name="ImportEdgeBuilder",
                    confidence_source=res.resolution_strategy,
                    explanation=f"Import statement '{stmt.imported_target_raw}' resolved via '{res.resolution_strategy}'."
                )

                meta = EdgeMetadata(
                    language={"lang": stmt.language.value},
                    custom={
                        "imported_target_raw": stmt.imported_target_raw,
                        "alias": stmt.alias,
                        "is_relative": stmt.is_relative,
                        "relative_level": stmt.relative_level,
                        "is_wildcard": stmt.is_wildcard,
                        "resolved_fqn": res.resolved_fqn
                    }
                )

                edge = Edge(
                    id=eid,
                    source_symbol_id=stmt.source_symbol_id,
                    target_symbol_id=res.target_symbol_id,
                    kind=EdgeKind.IMPORT,
                    direction=EdgeDirection.DIRECTED,
                    strength=EdgeStrength.NORMAL,
                    confidence=res.confidence,
                    language=stmt.language,
                    repository_id=repository_id,
                    file_path=stmt.source_file_path,
                    evidence=ev,
                    attributes=EdgeAttributes(),
                    origin=EdgeOrigin(creator="devbrain.import_edge_builder", stage="Step 4.2"),
                    version=EdgeVersion(),
                    metadata=meta
                )

                edge_list.append(edge)
                by_id[edge.id] = edge
                by_src.setdefault(edge.source_symbol_id, []).append(edge.id)
                by_tgt.setdefault(edge.target_symbol_id, []).append(edge.id)
                by_kind.setdefault(EdgeKind.IMPORT, []).append(edge.id)

                lang_str = stmt.language.value
                per_lang_counts[lang_str] = per_lang_counts.get(lang_str, 0) + 1

            except Exception as e:
                diagnostics = diagnostics.add_error(
                    message=f"Error constructing import edge for target '{stmt.imported_target_raw}': {str(e)}",
                    file_path=stmt.source_file_path,
                    code="ERR_IMPORT_EDGE_BUILD_FAILED"
                )

        coll_stats = EdgeStatistics(
            total_edges=len(edge_list),
            edges_by_kind_counts={"import": len(edge_list)},
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
        ImportEdgeValidator.validate(collection)

        return collection
