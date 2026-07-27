"""
Execution Plan Structural & DAG Validation.

Enforces stage dependency DAG acyclicity, operator integrity, and runtime metadata bounds.
"""

from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field

from graph_query_engine.execution.plan import ExecutionPlan


class ExecutionValidationViolation(BaseModel):
    """
    Immutable violation item produced by ExecutionPlanValidator.
    """
    model_config = ConfigDict(frozen=True)

    rule_id: str = Field(..., description="Unique validation rule ID")
    message: str = Field(..., description="Violation message string")
    stage_id: Optional[str] = Field(default=None, description="Associated stage ID")
    severity: str = Field(default="ERROR", description="Severity: WARNING, ERROR")


class ExecutionValidationReport(BaseModel):
    """
    Immutable report produced by ExecutionPlanValidator.
    """
    model_config = ConfigDict(frozen=True)

    is_valid: bool = Field(..., description="True if zero ERROR violations exist")
    violations: List[ExecutionValidationViolation] = Field(default_factory=list, description="Recorded violations list")


class ExecutionPlanValidator:
    """
    Validator verifying ExecutionPlan structural and DAG invariants.
    """

    @classmethod
    def validate(cls, plan: ExecutionPlan) -> ExecutionValidationReport:
        """Validates an ExecutionPlan object."""
        violations: List[ExecutionValidationViolation] = []

        if not plan.execution_plan_id:
            violations.append(ExecutionValidationViolation(rule_id="EVAL_001_PLAN_ID", message="ExecutionPlan execution_plan_id cannot be empty."))
        if not plan.physical_plan_id:
            violations.append(ExecutionValidationViolation(rule_id="EVAL_002_PHYSICAL_PLAN_ID", message="ExecutionPlan physical_plan_id cannot be empty."))

        # 1. DAG acyclicity check
        if not plan.dependency_graph.is_acyclic():
            violations.append(ExecutionValidationViolation(rule_id="EVAL_003_DAG_CYCLE", message="ExecutionPlan stage dependency graph contains cycles."))

        # 2. Stage validation
        known_stage_ids = set(s.stage_id for s in plan.stages)
        for stage in plan.stages:
            for err in stage.validate_stage():
                violations.append(ExecutionValidationViolation(rule_id="EVAL_004_STAGE_CONFIG", message=err, stage_id=stage.stage_id))
            for dep in stage.dependencies:
                if dep not in known_stage_ids:
                    violations.append(
                        ExecutionValidationViolation(
                            rule_id="EVAL_005_MISSING_DEP",
                            message=f"ExecutionStage '{stage.stage_id}' references unknown dependency stage '{dep}'.",
                            stage_id=stage.stage_id,
                        )
                    )

        is_valid = not any(v.severity == "ERROR" for v in violations)
        return ExecutionValidationReport(is_valid=is_valid, violations=violations)


__all__ = [
    "ExecutionValidationViolation",
    "ExecutionValidationReport",
    "ExecutionPlanValidator",
]
