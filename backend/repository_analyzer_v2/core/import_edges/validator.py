"""
core/import_edges/validator.py
-------------------------------
Import EdgeCollection Integrity Validator.
"""

from __future__ import annotations

from core.edges import EdgeCollection, EdgeKind
from core.import_edges.diagnostics import ImportEdgeDiagnostics


class ImportEdgeValidator:
    """
    Validates that an EdgeCollection contains exclusively EdgeKind.IMPORT edges.
    """

    @classmethod
    def validate(cls, collection: EdgeCollection) -> ImportEdgeDiagnostics:
        diagnostics = ImportEdgeDiagnostics()

        for edge in collection.edges:
            if edge.kind != EdgeKind.IMPORT:
                diagnostics = diagnostics.add_error(
                    message=f"Non-import edge kind '{edge.kind}' detected in Import EdgeCollection.",
                    file_path=edge.file_path,
                    code="ERR_INVALID_EDGE_KIND"
                )

        return diagnostics
