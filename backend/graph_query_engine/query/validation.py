"""
Query Validation Infrastructure.

Validates structural correctness of EngineeringQuery representations.
DOES NOT perform planning, cost model, physical planning, or graph execution.
"""

from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field

from graph_query_engine.query.diagnostics import SourceLocation
from graph_query_engine.query.model import EngineeringQuery
from graph_query_engine.query.visitor import ValidationVisitor


class ValidationViolation(BaseModel):
    """
    Immutable representation of a structural query validation error or warning.
    """
    model_config = ConfigDict(frozen=True)

    rule_id: str = Field(..., description="Unique validation rule ID")
    message: str = Field(..., description="Human readable violation message")
    severity: str = Field(default="ERROR", description="Severity: WARNING, ERROR")
    location: Optional[SourceLocation] = Field(default=None, description="Optional source location")


class ValidationReport(BaseModel):
    """
    Immutable validation report produced by QueryValidator.
    """
    model_config = ConfigDict(frozen=True)

    is_valid: bool = Field(..., description="True if zero ERROR violations exist")
    violations: List[ValidationViolation] = Field(default_factory=list, description="Recorded violations list")

    def count_errors(self) -> int:
        """Returns count of ERROR severity violations."""
        return sum(1 for v in self.violations if v.severity == "ERROR")

    def count_warnings(self) -> int:
        """Returns count of WARNING severity violations."""
        return sum(1 for v in self.violations if v.severity == "WARNING")


class QueryValidator:
    """
    Infrastructure validator for EngineeringQuery structural representation.
    """

    @classmethod
    def validate(cls, query: EngineeringQuery) -> ValidationReport:
        """
        Validates an EngineeringQuery for required fields, type bounds, and AST integrity.
        """
        violations: List[ValidationViolation] = []

        # 1. Validate query identity & metadata
        if not str(query.query_id):
            violations.append(
                ValidationViolation(
                    rule_id="RULE_001_QUERY_ID",
                    message="EngineeringQuery query_id must not be empty.",
                )
            )

        # 2. Validate AST structure using ValidationVisitor
        visitor = ValidationVisitor()
        ast_errors = visitor.validate(query)
        for err in ast_errors:
            violations.append(
                ValidationViolation(
                    rule_id="RULE_002_AST_STRUCTURE",
                    message=err,
                )
            )

        # 3. Validate constraints
        c = query.constraints
        if c.time_budget.max_seconds <= 0:
            violations.append(
                ValidationViolation(
                    rule_id="RULE_003_TIME_BUDGET",
                    message="TimeBudgetConstraint max_seconds must be positive.",
                )
            )
        if c.memory_budget.max_bytes <= 0:
            violations.append(
                ValidationViolation(
                    rule_id="RULE_004_MEMORY_BUDGET",
                    message="MemoryBudgetConstraint max_bytes must be positive.",
                )
            )

        # Determine validity
        is_valid = not any(v.severity == "ERROR" for v in violations)
        return ValidationReport(is_valid=is_valid, violations=violations)


__all__ = [
    "ValidationViolation",
    "ValidationReport",
    "QueryValidator",
]
