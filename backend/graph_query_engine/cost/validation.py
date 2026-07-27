"""
Cost Model Validation Infrastructure.

Enforces invariants on CostEstimate and CostReport objects:
- Non-negative cost metrics
- Confidence scores within [0.0, 1.0]
- Complete operator breakdowns
"""

from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field

from graph_query_engine.cost.estimate import CostEstimate, CostReport


class CostValidationViolation(BaseModel):
    """
    Immutable violation item produced by CostValidator.
    """
    model_config = ConfigDict(frozen=True)

    rule_id: str = Field(..., description="Unique validation rule ID")
    message: str = Field(..., description="Violation message string")
    operator_id: Optional[str] = Field(default=None, description="Associated operator ID")
    severity: str = Field(default="ERROR", description="Severity: WARNING, ERROR")


class CostValidationReport(BaseModel):
    """
    Immutable report produced by CostValidator.
    """
    model_config = ConfigDict(frozen=True)

    is_valid: bool = Field(..., description="True if zero ERROR violations exist")
    violations: List[CostValidationViolation] = Field(default_factory=list, description="Recorded violations list")


class CostValidator:
    """
    Validator enforcing invariants on CostEstimate and CostReport instances.
    """

    @classmethod
    def validate_estimate(cls, estimate: CostEstimate, operator_id: Optional[str] = None) -> List[CostValidationViolation]:
        """Validates an individual CostEstimate instance."""
        violations: List[CostValidationViolation] = []

        if estimate.cpu_cost < 0:
            violations.append(CostValidationViolation(rule_id="CVAL_001_CPU_NEG", message="cpu_cost cannot be negative.", operator_id=operator_id))
        if estimate.memory_cost < 0:
            violations.append(CostValidationViolation(rule_id="CVAL_002_MEM_NEG", message="memory_cost cannot be negative.", operator_id=operator_id))
        if estimate.traversal_cost < 0:
            violations.append(CostValidationViolation(rule_id="CVAL_003_TRAV_NEG", message="traversal_cost cannot be negative.", operator_id=operator_id))
        if not (0.0 <= estimate.confidence_score <= 1.0):
            violations.append(CostValidationViolation(rule_id="CVAL_004_CONF_BOUNDS", message="confidence_score must be between 0.0 and 1.0.", operator_id=operator_id))

        return violations

    @classmethod
    def validate_report(cls, report: CostReport) -> CostValidationReport:
        """Validates an entire CostReport object."""
        violations: List[CostValidationViolation] = []

        if not report.report_id:
            violations.append(CostValidationViolation(rule_id="CVAL_005_REPORT_ID", message="CostReport report_id cannot be empty."))
        if not report.plan_id:
            violations.append(CostValidationViolation(rule_id="CVAL_006_PLAN_ID", message="CostReport plan_id cannot be empty."))

        # Validate total plan estimate
        violations.extend(cls.validate_estimate(report.total_cost_estimate))

        # Validate per-operator estimates
        for op_breakdown in report.operator_costs:
            violations.extend(cls.validate_estimate(op_breakdown.estimate, operator_id=op_breakdown.operator_id))

        is_valid = not any(v.severity == "ERROR" for v in violations)
        return CostValidationReport(is_valid=is_valid, violations=violations)


__all__ = [
    "CostValidationViolation",
    "CostValidationReport",
    "CostValidator",
]
