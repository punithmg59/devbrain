"""
core/graph_validation/validator.py
-----------------------------------
DependencyGraphValidator Facade Entrypoint executing 7-category graph verification rules.
"""

from __future__ import annotations

import time
from typing import Dict, Set

from core.dependency_graph import DependencyGraph, hash_dependency_graph
from core.graph_validation.diagnostics import ValidationCategory, ValidationDiagnostics
from core.graph_validation.report import DependencyGraphValidationReport
from core.graph_validation.statistics import ValidationStatistics


class DependencyGraphValidator:
    """
    Read-only validation framework that inspects a DependencyGraph across 7 validation categories.
    """

    @classmethod
    def validate(cls, graph: DependencyGraph) -> DependencyGraphValidationReport:
        start_time = time.perf_counter()
        diagnostics = ValidationDiagnostics()
        rules_evaluated = 0

        # Category 1: Structural Validation
        diagnostics, r1 = cls._validate_structure(graph, diagnostics)
        rules_evaluated += r1

        # Category 2: Reference Validation
        diagnostics, r2 = cls._validate_references(graph, diagnostics)
        rules_evaluated += r2

        # Category 3: Index Validation
        diagnostics, r3 = cls._validate_indexes(graph, diagnostics)
        rules_evaluated += r3

        # Category 4: Metadata Validation
        diagnostics, r4 = cls._validate_metadata(graph, diagnostics)
        rules_evaluated += r4

        # Category 5: Version Validation
        diagnostics, r5 = cls._validate_version(graph, diagnostics)
        rules_evaluated += r5

        # Category 6: Integrity Validation
        graph_hash = hash_dependency_graph(graph)
        diagnostics, r6 = cls._validate_integrity(graph, graph_hash, diagnostics)
        rules_evaluated += r6

        # Category 7: Performance & Topology Validation
        orphan_count, diagnostics, r7 = cls._validate_performance(graph, diagnostics)
        rules_evaluated += r7

        # Statistics & Report Assembly
        errors_by_cat: Dict[str, int] = {}
        warnings_by_cat: Dict[str, int] = {}

        for d in diagnostics.diagnostics:
            cat_str = d.category.value
            if d.severity.value == "error":
                errors_by_cat[cat_str] = errors_by_cat.get(cat_str, 0) + 1
            else:
                warnings_by_cat[cat_str] = warnings_by_cat.get(cat_str, 0) + 1

        stats = ValidationStatistics(
            total_nodes_validated=len(graph.canonical_symbols.symbols),
            total_edges_validated=len(graph.edges),
            orphan_nodes_count=orphan_count,
            rules_evaluated_count=rules_evaluated,
            errors_by_category=errors_by_cat,
            warnings_by_category=warnings_by_cat,
            duration_ms=(time.perf_counter() - start_time) * 1000.0
        )

        is_valid = not diagnostics.has_errors
        err_len = len(diagnostics.errors)
        warn_len = len(diagnostics.warnings)

        summary_text = (
            f"Graph Validation {'PASSED' if is_valid else 'FAILED'} for repository '{graph.repository_id}'. "
            f"Validated {stats.total_nodes_validated} nodes and {stats.total_edges_validated} edges. "
            f"Errors: {err_len}, Warnings: {warn_len} across {rules_evaluated} rules evaluated."
        )

        return DependencyGraphValidationReport(
            is_valid=is_valid,
            repository_id=graph.repository_id,
            validated_graph_hash=graph_hash,
            total_nodes_validated=stats.total_nodes_validated,
            total_edges_validated=stats.total_edges_validated,
            error_count=err_len,
            warning_count=warn_len,
            diagnostics=diagnostics,
            statistics=stats,
            summary=summary_text
        )

    @classmethod
    def _validate_structure(cls, graph: DependencyGraph, diags: ValidationDiagnostics) -> tuple[ValidationDiagnostics, int]:
        rules = 0
        seen_node_ids: Set[str] = set()
        for sym in graph.canonical_symbols.symbols:
            rules += 1
            sid_str = sym.id.value
            if sid_str in seen_node_ids:
                diags = diags.add_error(
                    message=f"Duplicate NodeID '{sid_str}' detected in canonical symbols.",
                    category=ValidationCategory.STRUCTURAL,
                    file_path=sym.file_path,
                    code="ERR_DUPLICATE_NODE_ID"
                )
            seen_node_ids.add(sid_str)

        seen_edge_ids: Set[str] = set()
        for edge in graph.edges:
            rules += 1
            eid_str = edge.id.value
            if eid_str in seen_edge_ids:
                diags = diags.add_error(
                    message=f"Duplicate EdgeID '{eid_str}' detected in graph edges.",
                    category=ValidationCategory.STRUCTURAL,
                    file_path=edge.file_path,
                    code="ERR_DUPLICATE_EDGE_ID"
                )
            seen_edge_ids.add(eid_str)

            # Check source node
            src_val = edge.source_symbol_id.value
            if src_val not in graph.indexes.nodes_by_id:
                diags = diags.add_error(
                    message=f"Dangling source SymbolID '{src_val}' in edge '{eid_str}'.",
                    category=ValidationCategory.STRUCTURAL,
                    file_path=edge.file_path,
                    code="ERR_DANGLING_SOURCE_SYMBOL"
                )

            # Check target node
            tgt_val = edge.target_symbol_id.value
            if tgt_val not in graph.indexes.nodes_by_id and not tgt_val.startswith("sym_unresolved_"):
                diags = diags.add_warning(
                    message=f"Unresolved target SymbolID '{tgt_val}' in edge '{eid_str}'.",
                    category=ValidationCategory.STRUCTURAL,
                    file_path=edge.file_path,
                    code="WARN_UNRESOLVED_TARGET_SYMBOL"
                )

        return diags, rules

    @classmethod
    def _validate_references(cls, graph: DependencyGraph, diags: ValidationDiagnostics) -> tuple[ValidationDiagnostics, int]:
        rules = 0
        for sym in graph.canonical_symbols.symbols:
            rules += 1
            if not sym.id.value.startswith("sym_"):
                diags = diags.add_error(
                    message=f"Malformed SymbolID prefix in '{sym.id.value}'. Must start with 'sym_'.",
                    category=ValidationCategory.REFERENCE,
                    file_path=sym.file_path,
                    code="ERR_MALFORMED_SYMBOL_ID"
                )

        for edge in graph.edges:
            rules += 1
            if not edge.id.value.startswith("edge_"):
                diags = diags.add_error(
                    message=f"Malformed EdgeID prefix in '{edge.id.value}'. Must start with 'edge_'.",
                    category=ValidationCategory.REFERENCE,
                    file_path=edge.file_path,
                    code="ERR_MALFORMED_EDGE_ID"
                )

        return diags, rules

    @classmethod
    def _validate_indexes(cls, graph: DependencyGraph, diags: ValidationDiagnostics) -> tuple[ValidationDiagnostics, int]:
        rules = 0
        # Verify edge count matches indexes.edges_by_id length
        rules += 1
        if len(graph.edges) != len(graph.indexes.edges_by_id):
            diags = diags.add_error(
                message=f"Graph edges count ({len(graph.edges)}) does not match index edges_by_id count ({len(graph.indexes.edges_by_id)}).",
                category=ValidationCategory.INDEX,
                code="ERR_EDGE_INDEX_MISMATCH"
            )

        # Verify node count matches indexes.nodes_by_id length
        rules += 1
        if len(graph.canonical_symbols.symbols) != len(graph.indexes.nodes_by_id):
            diags = diags.add_error(
                message=f"Canonical symbols count ({len(graph.canonical_symbols.symbols)}) does not match index nodes_by_id count ({len(graph.indexes.nodes_by_id)}).",
                category=ValidationCategory.INDEX,
                code="ERR_NODE_INDEX_MISMATCH"
            )

        return diags, rules

    @classmethod
    def _validate_metadata(cls, graph: DependencyGraph, diags: ValidationDiagnostics) -> tuple[ValidationDiagnostics, int]:
        rules = 0
        for sym in graph.canonical_symbols.symbols:
            rules += 1
            if not sym.file_path:
                diags = diags.add_error(
                    message=f"Symbol '{sym.id.value}' has empty file_path.",
                    category=ValidationCategory.METADATA,
                    code="ERR_EMPTY_FILE_PATH"
                )

        return diags, rules

    @classmethod
    def _validate_version(cls, graph: DependencyGraph, diags: ValidationDiagnostics) -> tuple[ValidationDiagnostics, int]:
        rules = 1
        if graph.version != "4.6.0":
            diags = diags.add_warning(
                message=f"DependencyGraph semver '{graph.version}' differs from expected '4.6.0'.",
                category=ValidationCategory.VERSION,
                code="WARN_VERSION_MISMATCH"
            )
        return diags, rules

    @classmethod
    def _validate_integrity(cls, graph: DependencyGraph, graph_hash: str, diags: ValidationDiagnostics) -> tuple[ValidationDiagnostics, int]:
        rules = 1
        if not graph_hash or len(graph_hash) != 64:
            diags = diags.add_error(
                message="Failed to generate valid cryptographic SHA-256 graph hash.",
                category=ValidationCategory.INTEGRITY,
                code="ERR_INVALID_GRAPH_HASH"
            )
        return diags, rules

    @classmethod
    def _validate_performance(cls, graph: DependencyGraph, diags: ValidationDiagnostics) -> tuple[int, ValidationDiagnostics, int]:
        rules = 0
        orphan_count = 0
        for sym in graph.canonical_symbols.symbols:
            rules += 1
            sid_str = sym.id.value
            has_out = bool(graph.indexes.outgoing_edges.get(sid_str))
            has_inc = bool(graph.indexes.incoming_edges.get(sid_str))
            if not has_out and not has_inc:
                orphan_count += 1

        if orphan_count > 0:
            diags = diags.add_warning(
                message=f"Detected {orphan_count} orphan node(s) with zero incoming or outgoing edges.",
                category=ValidationCategory.PERFORMANCE,
                code="WARN_ORPHAN_NODES"
            )

        return orphan_count, diags, rules
