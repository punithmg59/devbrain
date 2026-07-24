"""
analysis/call_graph/validator.py
---------------------------------
Phase 4.8.3 — Read-Only Graph Validation & Integrity Engine.

Provides `GraphValidator`, a high-performance linear-time O(V + E) validation
engine that executes modular validation rules across CallGraph and GraphIndex objects.

Design Principles
-----------------
- **Strictly Read-Only**: Inspects graph entities without mutating nodes, edges, or indexes.
- **Zero Data Repair**: Reports and categorizes issues into INFO, WARNING, ERROR, CRITICAL
  without altering data contracts.
- **Linear-Time Performance**: O(V + E) single-pass rule execution with zero nested array scans.
- **Structured Output**: Produces `GraphValidationResult` containing `ValidationReport`
  and telemetry metrics.
"""

from __future__ import annotations

import time
from typing import List, Optional

from models.graph_models import CallGraph, CallGraphResult
from models.graph_index_models import GraphIndex, CallGraphIndexResult
from models.graph_validation_models import (
    GraphValidationResult,
    ValidationIssue,
    ValidationMetrics,
    ValidationReport,
    ValidationSeverity,
)
from analysis.call_graph.validation_rules import (
    BaseValidationRule,
    EdgeValidationRule,
    GraphConsistencyRule,
    IndexValidationRule,
    NodeValidationRule,
    ReferenceIntegrityRule,
    StructuralIntegrityRule,
)
from analysis.call_graph.metrics import compute_validation_metrics
from utils.logger import get_logger

logger = get_logger(__name__)


class GraphValidator:
    """
    Production-grade validation engine for CallGraph and GraphIndex objects.

    Usage::

        validator = GraphValidator(repository_id="repo1")
        val_result = validator.validate(call_graph, graph_index)
    """

    def __init__(
        self,
        repository_id: str = "repo",
        rules: Optional[List[BaseValidationRule]] = None,
    ) -> None:
        self.repository_id = repository_id
        self.rules = rules or [
            StructuralIntegrityRule(),
            NodeValidationRule(),
            EdgeValidationRule(),
            IndexValidationRule(),
            GraphConsistencyRule(),
            ReferenceIntegrityRule(),
        ]

    def validate(
        self,
        graph: CallGraph,
        graph_index: Optional[GraphIndex] = None,
    ) -> GraphValidationResult:
        """
        Execute all read-only validation rules over `CallGraph` and `GraphIndex`.

        Parameters
        ----------
        graph:
            Source `CallGraph` instance to validate.
        graph_index:
            Optional pre-computed `GraphIndex` instance to validate.

        Returns
        -------
        GraphValidationResult
        """
        start_time = time.perf_counter()
        logger.info(
            f"[GraphValidator] Starting read-only graph validation for repo '{self.repository_id}' "
            f"({len(self.rules)} rules configured)"
        )

        all_issues: List[ValidationIssue] = []

        # Stream rule execution
        for rule in self.rules:
            try:
                rule_issues = rule.validate(graph, graph_index)
                all_issues.extend(rule_issues)
            except Exception as exc:
                msg = f"Rule '{rule.__class__.__name__}' execution failed: {exc}"
                logger.error(f"[GraphValidator] {msg}")
                all_issues.append(
                    ValidationIssue(
                        severity=ValidationSeverity.CRITICAL,
                        code="RULE_EXECUTION_FAILURE",
                        category=rule.category,
                        message=msg,
                    )
                )

        # Categorize Issue Severities
        info_count = sum(1 for i in all_issues if i.severity == ValidationSeverity.INFO)
        warning_count = sum(1 for i in all_issues if i.severity == ValidationSeverity.WARNING)
        error_count = sum(1 for i in all_issues if i.severity == ValidationSeverity.ERROR)
        critical_count = sum(1 for i in all_issues if i.severity == ValidationSeverity.CRITICAL)

        is_valid = (error_count == 0) and (critical_count == 0)
        duration_ms = (time.perf_counter() - start_time) * 1000.0

        val_metrics = compute_validation_metrics(
            graph=graph,
            graph_index=graph_index,
            rules_executed=len(self.rules),
            info_count=info_count,
            warning_count=warning_count,
            error_count=error_count,
            critical_count=critical_count,
            validation_duration_ms=duration_ms,
        )

        report = ValidationReport(
            is_valid=is_valid,
            issues=all_issues,
            metrics=val_metrics,
            error_count=error_count + critical_count,
            warning_count=warning_count,
            critical_count=critical_count,
        )

        warnings_list = [i.message for i in all_issues if i.severity == ValidationSeverity.WARNING]
        errors_list = [i.message for i in all_issues if i.severity in (ValidationSeverity.ERROR, ValidationSeverity.CRITICAL)]

        logger.info(
            f"[GraphValidator] Validation completed: is_valid={is_valid}, "
            f"Errors={error_count + critical_count}, Warnings={warning_count}, Duration={duration_ms:.2f}ms"
        )

        return GraphValidationResult(
            repository_id=self.repository_id,
            validation_report=report,
            metrics=val_metrics,
            warnings=warnings_list,
            errors=errors_list,
        )

    def validate_result(self, call_graph_result: CallGraphResult) -> GraphValidationResult:
        """Helper method to validate from a `CallGraphResult` container."""
        return self.validate(graph=call_graph_result.graph)

    def validate_index_result(self, index_result: CallGraphIndexResult) -> GraphValidationResult:
        """Helper method to validate from a `CallGraphIndexResult` container."""
        return self.validate(graph=index_result.graph, graph_index=index_result.graph_index)


# Re-export CallGraphValidator for backward compatibility
class CallGraphValidator:
    """Backward compatibility wrapper delegating to GraphValidator."""

    def __init__(self, repository_id: str = "repo") -> None:
        self._validator = GraphValidator(repository_id=repository_id)

    def validate(self, graph: CallGraph) -> ValidationReport:
        val_res = self._validator.validate(graph)
        return val_res.validation_report
