"""
Public Query API Validation.

Validates QueryRequest structure, parameters, depth constraints, and repository scope before pipeline planning.
"""

from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field

from graph_query_engine.api.request import QueryRequest


class QueryValidationViolation(BaseModel):
    """Immutable record of a validation violation."""

    model_config = ConfigDict(frozen=True)

    field: str = Field(..., description="Target parameter or field name")
    message: str = Field(..., description="Violation description")
    severity: str = Field(default="ERROR", description="Severity ('ERROR' or 'WARNING')")


class QueryValidationReport(BaseModel):
    """Immutable validation summary report."""

    model_config = ConfigDict(frozen=True)

    is_valid: bool = Field(default=True, description="True if no ERROR violations were found")
    violations: List[QueryValidationViolation] = Field(default_factory=list, description="List of recorded violations")


class QueryValidation:
    """
    Validates Public Query API requests.
    """

    SUPPORTED_OPERATIONS = {
        "lookup_node", "lookup_nodes", "lookup_file", "lookup_folder",
        "lookup_class", "lookup_function", "lookup_method", "lookup_interface",
        "lookup_service", "lookup_api", "lookup_route", "lookup_symbol",
        "find_callers", "find_callees", "find_dependencies", "find_dependents",
        "find_imports", "find_exports", "find_neighbors", "find_related_nodes",
        "find_reachable_nodes", "find_paths", "find_shortest_path",
        "find_cycles", "find_connected_components",
        "execute_query", "execute_execution_plan", "execute_traversal",
        "query_repository", "search_repository", "search_symbols",
        "search_by_name", "search_by_type", "search_by_metadata", "search_by_annotation",
    }

    @classmethod
    def validate(cls, request: QueryRequest) -> QueryValidationReport:
        """Validates a QueryRequest and produces a QueryValidationReport."""
        violations: List[QueryValidationViolation] = []

        # 1. Operation check
        if not request.operation:
            violations.append(QueryValidationViolation(field="operation", message="Operation name cannot be empty."))
        elif request.operation not in cls.SUPPORTED_OPERATIONS:
            violations.append(
                QueryValidationViolation(
                    field="operation",
                    message=f"Unsupported operation '{request.operation}'.",
                )
            )

        # 2. Depth constraint check
        if request.context.depth_limit < 1:
            violations.append(
                QueryValidationViolation(
                    field="context.depth_limit",
                    message="Depth limit must be at least 1.",
                )
            )
        elif request.context.depth_limit > 100:
            violations.append(
                QueryValidationViolation(
                    field="context.depth_limit",
                    message="Depth limit cannot exceed 100.",
                    severity="WARNING",
                )
            )

        # 3. Max nodes limit check
        if request.context.max_nodes_limit < 1:
            violations.append(
                QueryValidationViolation(
                    field="context.max_nodes_limit",
                    message="Max nodes limit must be at least 1.",
                )
            )

        # 4. Timeout check
        if request.context.timeout_seconds <= 0.0:
            violations.append(
                QueryValidationViolation(
                    field="context.timeout_seconds",
                    message="Timeout seconds must be strictly positive.",
                )
            )

        has_error = any(v.severity == "ERROR" for v in violations)
        return QueryValidationReport(is_valid=not has_error, violations=violations)


__all__ = ["QueryValidationViolation", "QueryValidationReport", "QueryValidation"]
