"""
Physical Plan Structural & Strategy Validation.

Enforces physical operator invariants, tree node counts, and strategy consistency.
"""

from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field

from graph_query_engine.physical.operators import (
    HashJoinPhysicalOperator,
    MergeJoinPhysicalOperator,
    NestedLoopJoinPhysicalOperator,
)
from graph_query_engine.physical.plan import PhysicalPlan, PhysicalPlanNode


class PhysicalValidationViolation(BaseModel):
    """
    Immutable violation item produced by PhysicalPlanValidator.
    """
    model_config = ConfigDict(frozen=True)

    rule_id: str = Field(..., description="Unique validation rule ID")
    message: str = Field(..., description="Violation message string")
    operator_id: Optional[str] = Field(default=None, description="Associated operator ID")
    severity: str = Field(default="ERROR", description="Severity: WARNING, ERROR")


class PhysicalValidationReport(BaseModel):
    """
    Immutable report produced by PhysicalPlanValidator.
    """
    model_config = ConfigDict(frozen=True)

    is_valid: bool = Field(..., description="True if zero ERROR violations exist")
    violations: List[PhysicalValidationViolation] = Field(default_factory=list, description="Recorded violations list")


class PhysicalPlanValidator:
    """
    Validator verifying PhysicalPlan structural and strategy invariants.
    """

    @classmethod
    def validate(cls, plan: PhysicalPlan) -> PhysicalValidationReport:
        """Validates a PhysicalPlan object."""
        violations: List[PhysicalValidationViolation] = []

        if not plan.plan_id:
            violations.append(PhysicalValidationViolation(rule_id="PVAL_001_PLAN_ID", message="PhysicalPlan plan_id cannot be empty."))
        if not plan.logical_plan_id:
            violations.append(PhysicalValidationViolation(rule_id="PVAL_002_LOGICAL_PLAN_ID", message="PhysicalPlan logical_plan_id cannot be empty."))

        cls._validate_node(plan.root_node, violations)

        is_valid = not any(v.severity == "ERROR" for v in violations)
        return PhysicalValidationReport(is_valid=is_valid, violations=violations)

    @classmethod
    def _validate_node(cls, node: PhysicalPlanNode, violations: List[PhysicalValidationViolation]) -> None:
        op = node.operator

        for err in op.validate_operator():
            violations.append(PhysicalValidationViolation(rule_id="PVAL_003_OPERATOR_CONFIG", message=err, operator_id=op.operator_id))

        if isinstance(op, (HashJoinPhysicalOperator, NestedLoopJoinPhysicalOperator, MergeJoinPhysicalOperator)):
            if len(node.children) != 2:
                violations.append(
                    PhysicalValidationViolation(
                        rule_id="PVAL_004_JOIN_INPUTS",
                        message=f"Physical join operator '{op.operator_id}' must have exactly 2 child inputs (found {len(node.children)}).",
                        operator_id=op.operator_id,
                    )
                )

        for child in node.children:
            cls._validate_node(child, violations)


__all__ = [
    "PhysicalValidationViolation",
    "PhysicalValidationReport",
    "PhysicalPlanValidator",
]
