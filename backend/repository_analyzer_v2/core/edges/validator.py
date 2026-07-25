"""
core/edges/validator.py
------------------------
Integrity and Uniqueness Validator for Edge and EdgeCollection.
"""

from __future__ import annotations

from typing import Set

from core.edges.diagnostics import EdgeDiagnostics
from core.edges.ids import EdgeID
from core.edges.models import Edge


class EdgeValidator:
    """
    Validates structural integrity and EdgeID uniqueness for relationship edges.
    """

    @classmethod
    def validate(cls, edges: list[Edge], repository_id: str) -> EdgeDiagnostics:
        diagnostics = EdgeDiagnostics()
        seen_edge_ids: Set[EdgeID] = set()

        for edge in edges:
            # 1. EdgeID uniqueness check
            if edge.id in seen_edge_ids:
                diagnostics = diagnostics.add_error(
                    message=f"Duplicate EdgeID '{edge.id}' detected.",
                    file_path=edge.file_path,
                    code="ERR_DUPLICATE_EDGE_ID"
                )
            seen_edge_ids.add(edge.id)

            # 2. Repository matching check
            if edge.repository_id != repository_id:
                diagnostics = diagnostics.add_error(
                    message=f"Edge '{edge.id}' repository_id '{edge.repository_id}' mismatch with '{repository_id}'.",
                    file_path=edge.file_path,
                    code="ERR_REPO_ID_MISMATCH"
                )

            # 3. Confidence range check
            if not (0.0 <= edge.confidence <= 1.0):
                diagnostics = diagnostics.add_warning(
                    message=f"Edge '{edge.id}' confidence '{edge.confidence}' out of standard bounds [0.0, 1.0].",
                    file_path=edge.file_path,
                    code="WARN_INVALID_CONFIDENCE"
                )

        return diagnostics
