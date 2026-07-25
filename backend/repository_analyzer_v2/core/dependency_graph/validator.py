"""
core/dependency_graph/validator.py
-----------------------------------
DependencyGraph Structural & Integrity Validator.
"""

from __future__ import annotations

from core.dependency_graph.diagnostics import DependencyGraphDiagnostics
from core.dependency_graph.graph import DependencyGraph


class DependencyGraphValidator:
    """
    Validates the structural integrity and index consistency of a DependencyGraph.
    """

    @classmethod
    def validate(cls, graph: DependencyGraph) -> DependencyGraphDiagnostics:
        diagnostics = graph.diagnostics

        for edge in graph.edges:
            src_val = edge.source_symbol_id.value
            tgt_val = edge.target_symbol_id.value

            # Check source symbol exists in nodes
            if src_val not in graph.indexes.nodes_by_id:
                diagnostics = diagnostics.add_warning(
                    message=f"Edge '{edge.id}' source SymbolID '{edge.source_symbol_id}' not found in graph nodes.",
                    file_path=edge.file_path,
                    code="WARN_DANGLING_SOURCE_SYMBOL"
                )

            # Check target symbol exists or is synthetic unresolved placeholder
            if tgt_val not in graph.indexes.nodes_by_id and not tgt_val.startswith("sym_unresolved_"):
                diagnostics = diagnostics.add_warning(
                    message=f"Edge '{edge.id}' target SymbolID '{edge.target_symbol_id}' not found in graph nodes.",
                    file_path=edge.file_path,
                    code="WARN_DANGLING_TARGET_SYMBOL"
                )

        return diagnostics
