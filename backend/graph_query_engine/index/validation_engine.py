"""
Centralized IndexValidationEngine for Graph Query Engine.
"""

from typing import Iterable, Optional

from graph_query_engine.index.base import BaseIndex
from graph_query_engine.index.consistency_checker import IndexConsistencyChecker
from graph_query_engine.index.diagnostics import DiagnosticItem, DiagnosticSeverity, IndexDiagnostics
from graph_query_engine.index.edge_index import EdgeIndex
from graph_query_engine.index.health_report import HealthStatus, IndexHealthReport
from graph_query_engine.index.integrity_checker import IndexIntegrityChecker
from graph_query_engine.index.node_index import NodeIndex
from graph_query_engine.index.registry import IndexRegistry


class IndexValidationEngine:
    """
    Centralized validation engine validating registered indexes across integrity and cross-consistency categories.
    """

    @classmethod
    def validate_registry(cls, registry: IndexRegistry) -> IndexHealthReport:
        """
        Validates all active instances in registry and returns an IndexHealthReport.
        """
        all_diagnostics: list[DiagnosticItem] = []

        active_names = registry.list_indexes()
        active_indexes = [registry.get_index(name) for name in active_names if registry.get_index(name) is not None]

        # 1. Audit individual index integrity
        integrity_diag = IndexIntegrityChecker.check(active_indexes)
        all_diagnostics.extend(integrity_diag.items)

        # 2. Audit cross-index consistency if NodeIndex and EdgeIndex exist
        node_idx = registry.get_index("NodeIndex")
        edge_idx = registry.get_index("EdgeIndex")

        if isinstance(node_idx, NodeIndex):
            consist_diag = IndexConsistencyChecker.verify_consistency(
                node_index=node_idx,
                edge_index=edge_idx if isinstance(edge_idx, EdgeIndex) else None,
                other_indexes=active_indexes,
            )
            all_diagnostics.extend(consist_diag.items)

        diagnostics_model = IndexDiagnostics(items=tuple(all_diagnostics))

        status = HealthStatus.HEALTHY
        if diagnostics_model.has_errors:
            status = HealthStatus.FAILED
        elif diagnostics_model.warning_count > 0:
            status = HealthStatus.WARNING

        errs = tuple(item.message for item in diagnostics_model.items if item.severity in (DiagnosticSeverity.ERROR, DiagnosticSeverity.CRITICAL))
        warns = tuple(item.message for item in diagnostics_model.items if item.severity == DiagnosticSeverity.WARNING)
        recs = tuple(item.recommendation for item in diagnostics_model.items if item.recommendation)

        return IndexHealthReport(
            status=status,
            diagnostics=diagnostics_model,
            errors=errs,
            warnings=warns,
            recommendations=recs,
        )


__all__ = ["IndexValidationEngine"]
