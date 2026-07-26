"""
IndexIntegrityChecker for Auditing Index Models and Metadata Integrity.
"""

from typing import Iterable

from graph_query_engine.index.base import BaseIndex
from graph_query_engine.index.diagnostics import DiagnosticItem, DiagnosticSeverity, IndexDiagnostics


class IndexIntegrityChecker:
    """
    Integrity auditor inspecting BaseIndex models for duplicate IDs, missing metadata, or broken descriptors.
    """

    @classmethod
    def check(cls, indexes: Iterable[BaseIndex] | BaseIndex) -> IndexDiagnostics:
        """
        Audits index models and returns structured IndexDiagnostics findings.
        """
        index_list = [indexes] if isinstance(indexes, BaseIndex) else list(indexes)
        items: list[DiagnosticItem] = []

        seen_ids = set()

        for idx in index_list:
            if not idx.index_id:
                items.append(
                    DiagnosticItem(
                        code="ERR_INTEG_MISSING_ID",
                        severity=DiagnosticSeverity.ERROR,
                        component="BaseIndex",
                        message="Index instance has empty index_id.",
                        recommendation="Ensure IndexBuilder assigns non-empty unique index_id.",
                    )
                )
            elif idx.index_id in seen_ids:
                items.append(
                    DiagnosticItem(
                        code="ERR_INTEG_DUP_ID",
                        severity=DiagnosticSeverity.ERROR,
                        component="BaseIndex",
                        message=f"Duplicate index_id encountered: '{idx.index_id}'.",
                    )
                )
            seen_ids.add(idx.index_id)

            if not idx.descriptor.name:
                items.append(
                    DiagnosticItem(
                        code="ERR_INTEG_MISSING_NAME",
                        severity=DiagnosticSeverity.ERROR,
                        component="IndexDescriptor",
                        message="IndexDescriptor has empty name.",
                    )
                )

            if not idx.graph_identity.snapshot_id:
                items.append(
                    DiagnosticItem(
                        code="ERR_INTEG_MISSING_SNAP_ID",
                        severity=DiagnosticSeverity.ERROR,
                        component="GraphIdentity",
                        message="GraphIdentity reference has empty snapshot_id.",
                    )
                )

        return IndexDiagnostics(items=tuple(items))


__all__ = ["IndexIntegrityChecker"]
