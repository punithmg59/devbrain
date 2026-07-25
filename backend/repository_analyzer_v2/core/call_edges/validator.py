"""
core/call_edges/validator.py
-----------------------------
Call EdgeCollection Integrity Validator.
"""

from __future__ import annotations

from core.call_edges.diagnostics import CallEdgeDiagnostics
from core.edges import EdgeCollection, EdgeKind


class CallEdgeValidator:
    """
    Validates that an EdgeCollection contains exclusively EdgeKind.CALL edges.
    """

    @classmethod
    def validate(cls, collection: EdgeCollection) -> CallEdgeDiagnostics:
        diagnostics = CallEdgeDiagnostics()

        for edge in collection.edges:
            if edge.kind != EdgeKind.CALL:
                diagnostics = diagnostics.add_error(
                    message=f"Non-call edge kind '{edge.kind}' detected in Call EdgeCollection.",
                    file_path=edge.file_path,
                    code="ERR_INVALID_EDGE_KIND"
                )

        return diagnostics
