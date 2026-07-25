"""
core/inheritance_edges/validator.py
------------------------------------
Inheritance EdgeCollection Integrity Validator.
"""

from __future__ import annotations

from core.edges import EdgeCollection, EdgeKind
from core.inheritance_edges.diagnostics import InheritanceEdgeDiagnostics


class InheritanceEdgeValidator:
    """
    Validates that an EdgeCollection contains exclusively EdgeKind.INHERITANCE and EdgeKind.IMPLEMENTATION edges.
    """

    @classmethod
    def validate(cls, collection: EdgeCollection) -> InheritanceEdgeDiagnostics:
        diagnostics = InheritanceEdgeDiagnostics()

        for edge in collection.edges:
            if edge.kind not in (EdgeKind.INHERITANCE, EdgeKind.IMPLEMENTATION):
                diagnostics = diagnostics.add_error(
                    message=f"Invalid edge kind '{edge.kind}' detected in Inheritance EdgeCollection.",
                    file_path=edge.file_path,
                    code="ERR_INVALID_EDGE_KIND"
                )

            if edge.source_symbol_id == edge.target_symbol_id:
                diagnostics = diagnostics.add_error(
                    message=f"Circular self-inheritance detected for symbol '{edge.source_symbol_id}'.",
                    file_path=edge.file_path,
                    code="ERR_SELF_INHERITANCE"
                )

        return diagnostics
