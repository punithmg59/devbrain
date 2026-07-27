# backend/graph_query_engine/traversal/validation.py
"""Validation logic for graph traversal inputs, contexts, and results.
"""

from __future__ import annotations

from typing import Any, List, Optional
from pydantic import BaseModel, Field, ConfigDict

from .contracts import ITraversalStrategy
from .result import TraversalResult


class TraversalValidationViolation(BaseModel):
    """Immutable record of a traversal validation failure."""

    model_config = ConfigDict(frozen=True)

    severity: str = Field("ERROR", description="ERROR or WARNING")
    category: str = Field(..., description="Validation category (Graph, Plan, Operator, Constraints)")
    message: str = Field(..., description="Description of the violation")


class TraversalValidationReport(BaseModel):
    """Immutable summary report of traversal validation."""

    model_config = ConfigDict(frozen=True)

    valid: bool = Field(True, description="True if no ERROR severity violations exist")
    violations: List[TraversalValidationViolation] = Field(default_factory=list)


class TraversalValidator:
    """Stateless validator for graph traversal prerequisites and outputs."""

    @classmethod
    def validate_prerequisites(
        cls,
        graph_view: Any,
        start_nodes: List[str],
        max_depth: int = 100,
    ) -> TraversalValidationReport:
        violations: List[TraversalValidationViolation] = []

        if graph_view is None:
            violations.append(
                TraversalValidationViolation(category="Graph", message="GraphView instance cannot be None")
            )

        if not start_nodes:
            violations.append(
                TraversalValidationViolation(category="Plan", message="At least one root/start node must be provided")
            )

        if max_depth <= 0:
            violations.append(
                TraversalValidationViolation(category="Constraints", message="max_depth must be > 0")
            )

        # Check start node existence in graph_view if method exists
        if graph_view is not None and hasattr(graph_view, "has_node"):
            for node_id in start_nodes:
                if not graph_view.has_node(node_id):
                    violations.append(
                        TraversalValidationViolation(
                            severity="WARNING",
                            category="Graph",
                            message=f"Root node '{node_id}' does not exist in GraphView",
                        )
                    )

        has_errors = any(v.severity == "ERROR" for v in violations)
        return TraversalValidationReport(valid=not has_errors, violations=violations)

    @classmethod
    def validate_result(cls, result: TraversalResult) -> TraversalValidationReport:
        violations: List[TraversalValidationViolation] = []

        if not isinstance(result, TraversalResult):
            violations.append(
                TraversalValidationViolation(category="Result", message="Result must be a TraversalResult instance")
            )
            return TraversalValidationReport(valid=False, violations=violations)

        if result.execution_time_ms < 0:
            violations.append(
                TraversalValidationViolation(category="Metrics", message="execution_time_ms cannot be negative")
            )

        has_errors = any(v.severity == "ERROR" for v in violations)
        return TraversalValidationReport(valid=not has_errors, violations=violations)


__all__ = ["TraversalValidationViolation", "TraversalValidationReport", "TraversalValidator"]
