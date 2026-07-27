"""
Logical Plan Structural Validation Infrastructure.

Validates tree integrity, parent-child relationships, required operator fields, and plan consistency.
DOES NOT perform physical cost, index selection, or execution validation.
"""

from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field

from graph_query_engine.logical.operators import LogicalJoinOperator, LogicalOperator
from graph_query_engine.logical.plan import LogicalPlan, LogicalPlanNode


class LogicalValidationViolation(BaseModel):
    """
    Immutable violation item produced by LogicalPlanValidator.
    """
    model_config = ConfigDict(frozen=True)

    rule_id: str = Field(..., description="Unique validation rule ID")
    message: str = Field(..., description="Human readable violation message string")
    operator_id: Optional[str] = Field(default=None, description="Associated logical operator ID")
    severity: str = Field(default="ERROR", description="Severity: WARNING, ERROR")


class LogicalValidationReport(BaseModel):
    """
    Immutable report produced by LogicalPlanValidator.
    """
    model_config = ConfigDict(frozen=True)

    is_valid: bool = Field(..., description="True if zero ERROR violations exist")
    violations: List[LogicalValidationViolation] = Field(default_factory=list, description="Recorded violations list")

    def count_errors(self) -> int:
        """Returns count of ERROR severity violations."""
        return sum(1 for v in self.violations if v.severity == "ERROR")

    def count_warnings(self) -> int:
        """Returns count of WARNING severity violations."""
        return sum(1 for v in self.violations if v.severity == "WARNING")


class LogicalPlanValidator:
    """
    Structural validator verifying LogicalPlan invariants.
    """

    @classmethod
    def validate(cls, plan: LogicalPlan) -> LogicalValidationReport:
        """
        Validates a LogicalPlan for structural integrity and operator invariants.
        """
        violations: List[LogicalValidationViolation] = []

        # 1. Validate identity
        if not plan.plan_id:
            violations.append(
                LogicalValidationViolation(
                    rule_id="LVAL_001_PLAN_ID",
                    message="LogicalPlan plan_id cannot be empty.",
                )
            )
        if not str(plan.query_id):
            violations.append(
                LogicalValidationViolation(
                    rule_id="LVAL_002_QUERY_ID",
                    message="LogicalPlan query_id cannot be empty.",
                )
            )

        # 2. Validate tree nodes recursively
        cls._validate_node(plan.root_node, violations)

        is_valid = not any(v.severity == "ERROR" for v in violations)
        return LogicalValidationReport(is_valid=is_valid, violations=violations)

    @classmethod
    def _validate_node(cls, node: LogicalPlanNode, violations: List[LogicalValidationViolation]) -> None:
        op = node.operator

        # Operator self validation
        op_errs = op.validate_operator()
        for err in op_errs:
            violations.append(
                LogicalValidationViolation(
                    rule_id="LVAL_003_OPERATOR_CONFIG",
                    message=err,
                    operator_id=op.operator_id,
                )
            )

        # Join operator must have exactly 2 input children
        if isinstance(op, LogicalJoinOperator) and len(node.children) != 2:
            violations.append(
                LogicalValidationViolation(
                    rule_id="LVAL_004_JOIN_CHILDREN",
                    message=f"LogicalJoinOperator '{op.operator_id}' must have exactly 2 child inputs (found {len(node.children)}).",
                    operator_id=op.operator_id,
                )
            )

        # Recurse children
        for child in node.children:
            cls._validate_node(child, violations)


__all__ = [
    "LogicalValidationViolation",
    "LogicalValidationReport",
    "LogicalPlanValidator",
]
