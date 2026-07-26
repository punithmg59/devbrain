"""
IndexConsistencyChecker for Cross-Index Integrity Verification.
"""

from typing import Iterable
from graph_query_engine.index.base import BaseIndex
from graph_query_engine.index.diagnostics import DiagnosticItem, DiagnosticSeverity, IndexDiagnostics
from graph_query_engine.index.edge_index import EdgeIndex
from graph_query_engine.index.node_index import NodeIndex


class IndexConsistencyChecker:
    """
    Checker inspecting sets of active indexes for cross-index node and edge reference consistency.
    """

    @classmethod
    def verify_consistency(
        cls,
        node_index: NodeIndex,
        edge_index: EdgeIndex,
        other_indexes: Iterable[BaseIndex] = (),
    ) -> IndexDiagnostics:
        """
        Verifies that all edge source and target node IDs exist within node_index.
        """
        items: list[DiagnosticItem] = []

        if node_index is None:
            items.append(
                DiagnosticItem(
                    code="ERR_CONSISTENCY_NO_NODE_IDX",
                    severity=DiagnosticSeverity.ERROR,
                    component="NodeIndex",
                    message="NodeIndex is null or missing from consistency check.",
                )
            )
            return IndexDiagnostics(items=tuple(items))

        if edge_index is not None:
            for edge in edge_index.values():
                if not node_index.contains(edge.source_node_id):
                    items.append(
                        DiagnosticItem(
                            code="ERR_CONSISTENCY_DANGLING_SRC",
                            severity=DiagnosticSeverity.ERROR,
                            component="EdgeIndex",
                            message=f"Edge '{edge.edge_id}' references non-existent source NodeId '{edge.source_node_id}'.",
                        )
                    )
                if not node_index.contains(edge.target_node_id):
                    items.append(
                        DiagnosticItem(
                            code="ERR_CONSISTENCY_DANGLING_TGT",
                            severity=DiagnosticSeverity.ERROR,
                            component="EdgeIndex",
                            message=f"Edge '{edge.edge_id}' references non-existent target NodeId '{edge.target_node_id}'.",
                        )
                    )

        return IndexDiagnostics(items=tuple(items))


__all__ = ["IndexConsistencyChecker"]
