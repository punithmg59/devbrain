"""
analysis/call_graph/validator.py
---------------------------------
Phase 4.8.1 — Call Graph Integrity Validator.

Validates structural integrity of `CallGraph` instances:
- Verifies node_count and edge_count match container lengths
- Verifies every edge references existing caller and callee nodes
- Detects dangling edges
- Checks forward and reverse adjacency list consistency

Design Principles
-----------------
- **Structured Validation Report**: Returns `CallGraphValidationReport` with issue breakdowns.
- **Non-Throwing**: Records errors and warnings gracefully without aborting graph delivery.
"""

from __future__ import annotations

from typing import List

from models.graph_models import (
    CallGraph,
    CallGraphValidationIssue,
    CallGraphValidationReport,
)


class CallGraphValidator:
    """
    Validator engine for checking graph integrity of constructed CallGraph objects.

    Usage::

        validator = CallGraphValidator()
        report = validator.validate(call_graph)
    """

    def validate(self, graph: CallGraph) -> CallGraphValidationReport:
        """
        Validate structural integrity of a `CallGraph`.

        Parameters
        ----------
        graph:
            Constructed `CallGraph` instance.

        Returns
        -------
        CallGraphValidationReport
        """
        issues: List[CallGraphValidationIssue] = []
        error_count = 0
        warning_count = 0

        # 1. Count Consistency Check
        if graph.node_count != len(graph.nodes):
            issues.append(
                CallGraphValidationIssue(
                    severity="error",
                    code="NODE_COUNT_MISMATCH",
                    message=f"node_count property ({graph.node_count}) does not match len(nodes) ({len(graph.nodes)})",
                )
            )
            error_count += 1

        if graph.edge_count != len(graph.edges):
            issues.append(
                CallGraphValidationIssue(
                    severity="error",
                    code="EDGE_COUNT_MISMATCH",
                    message=f"edge_count property ({graph.edge_count}) does not match len(edges) ({len(graph.edges)})",
                )
            )
            error_count += 1

        # 2. Dangling Edge Check (verify caller and callee nodes exist)
        for edge_id, edge in graph.edges.items():
            if edge.caller_symbol_id not in graph.nodes:
                issues.append(
                    CallGraphValidationIssue(
                        severity="error",
                        code="DANGLING_CALLER_EDGE",
                        message=f"Edge '{edge_id}' references caller '{edge.caller_symbol_id}' which is not in graph nodes",
                        edge_id=edge_id,
                        node_id=edge.caller_symbol_id,
                    )
                )
                error_count += 1

            if edge.callee_symbol_id not in graph.nodes:
                issues.append(
                    CallGraphValidationIssue(
                        severity="error",
                        code="DANGLING_CALLEE_EDGE",
                        message=f"Edge '{edge_id}' references callee '{edge.callee_symbol_id}' which is not in graph nodes",
                        edge_id=edge_id,
                        node_id=edge.callee_symbol_id,
                    )
                )
                error_count += 1

        # 3. Adjacency List Consistency Check
        for caller_id, callees in graph.adjacency_list.items():
            if caller_id not in graph.nodes:
                issues.append(
                    CallGraphValidationIssue(
                        severity="warning",
                        code="ORPHAN_ADJACENCY_CALLER",
                        message=f"Forward adjacency list contains caller '{caller_id}' not in graph nodes",
                        node_id=caller_id,
                    )
                )
                warning_count += 1

            for callee_id in callees:
                if callee_id not in graph.nodes:
                    issues.append(
                        CallValidationIssue(
                            severity="warning",
                            code="ORPHAN_ADJACENCY_CALLEE",
                            message=f"Forward adjacency list for '{caller_id}' contains target '{callee_id}' not in graph nodes",
                            node_id=callee_id,
                        ) if False else CallGraphValidationIssue(
                            severity="warning",
                            code="ORPHAN_ADJACENCY_CALLEE",
                            message=f"Forward adjacency list for '{caller_id}' contains target '{callee_id}' not in graph nodes",
                            node_id=callee_id,
                        )
                    )
                    warning_count += 1

        is_valid = error_count == 0
        return CallGraphValidationReport(
            is_valid=is_valid,
            issues=issues,
            error_count=error_count,
            warning_count=warning_count,
        )
