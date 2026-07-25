"""
core/type_reference_edges/validator.py
---------------------------------------
Type Reference EdgeCollection Integrity Validator.
"""

from __future__ import annotations

from core.edges import EdgeCollection, EdgeKind
from core.type_reference_edges.diagnostics import TypeReferenceEdgeDiagnostics


class TypeReferenceEdgeValidator:
    """
    Validates that an EdgeCollection contains exclusively EdgeKind.TYPE_REFERENCE edges.
    """

    @classmethod
    def validate(cls, collection: EdgeCollection) -> TypeReferenceEdgeDiagnostics:
        diagnostics = TypeReferenceEdgeDiagnostics()

        for edge in collection.edges:
            if edge.kind != EdgeKind.TYPE_REFERENCE:
                diagnostics = diagnostics.add_error(
                    message=f"Non-type-reference edge kind '{edge.kind}' detected in Type Reference EdgeCollection.",
                    file_path=edge.file_path,
                    code="ERR_INVALID_EDGE_KIND"
                )

        return diagnostics
