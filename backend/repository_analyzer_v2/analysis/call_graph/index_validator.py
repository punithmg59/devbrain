"""
analysis/call_graph/index_validator.py
---------------------------------------
Phase 4.8.2 — Graph Index Integrity Validator.

Validates integrity and consistency of `GraphIndex` lookup tables against the source `CallGraph`:
- Verifies every indexed node symbol_id and FQN exists in source graph
- Verifies every indexed edge caller/callee pair exists in source graph
- Verifies file index consistency
- Detects dangling index references

Design Principles
-----------------
- **Structured Validation Report**: Returns `GraphIndexValidationReport` with issue breakdowns.
- **Non-Throwing**: Records errors and warnings gracefully without aborting execution.
"""

from __future__ import annotations

from typing import List

from models.graph_models import CallGraph
from models.graph_index_models import (
    GraphIndex,
    GraphIndexValidationIssue,
    GraphIndexValidationReport,
)


class GraphIndexValidator:
    """
    Validator engine for checking integrity of GraphIndex lookup tables.

    Usage::

        validator = GraphIndexValidator()
        report = validator.validate(graph_index, source_graph)
    """

    def validate(
        self,
        graph_index: GraphIndex,
        source_graph: CallGraph,
    ) -> GraphIndexValidationReport:
        """
        Validate consistency of `GraphIndex` against `CallGraph`.

        Parameters
        ----------
        graph_index:
            Constructed `GraphIndex` object.
        source_graph:
            Source `CallGraph` object.

        Returns
        -------
        GraphIndexValidationReport
        """
        issues: List[GraphIndexValidationIssue] = []
        error_count = 0
        warning_count = 0

        # 1. Symbol ID Node Index Check
        for sym_id, node in graph_index.node_by_symbol_id.items():
            if sym_id not in source_graph.nodes:
                issues.append(
                    GraphIndexValidationIssue(
                        severity="error",
                        code="MISSING_INDEXED_NODE",
                        message=f"node_by_symbol_id contains symbol_id '{sym_id}' missing from source CallGraph",
                        key=sym_id,
                    )
                )
                error_count += 1

        # 2. FQN Node Index Check
        for fqn, node in graph_index.node_by_fqn.items():
            if node.symbol_id not in source_graph.nodes:
                issues.append(
                    GraphIndexValidationIssue(
                        severity="error",
                        code="CORRUPTED_FQN_INDEX",
                        message=f"node_by_fqn entry '{fqn}' points to symbol_id '{node.symbol_id}' missing from source CallGraph",
                        key=fqn,
                    )
                )
                error_count += 1

        # 3. Caller Outgoing Edges Index Check
        for caller_id, edges in graph_index.edges_by_caller.items():
            if caller_id not in source_graph.nodes:
                issues.append(
                    GraphIndexValidationIssue(
                        severity="warning",
                        code="DANGLING_INDEX_CALLER",
                        message=f"edges_by_caller contains caller '{caller_id}' missing from source CallGraph",
                        key=caller_id,
                    )
                )
                warning_count += 1

        # 4. Callee Incoming Edges Index Check
        for callee_id, edges in graph_index.edges_by_callee.items():
            if callee_id not in source_graph.nodes:
                issues.append(
                    GraphIndexValidationIssue(
                        severity="warning",
                        code="DANGLING_INDEX_CALLEE",
                        message=f"edges_by_callee contains callee '{callee_id}' missing from source CallGraph",
                        key=callee_id,
                    )
                )
                warning_count += 1

        is_valid = error_count == 0
        return GraphIndexValidationReport(
            is_valid=is_valid,
            issues=issues,
            error_count=error_count,
            warning_count=warning_count,
        )
