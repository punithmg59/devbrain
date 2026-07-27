"""
Execution Plan SemVer Versioning Model.
"""

from pydantic import BaseModel, ConfigDict, Field


class ExecutionPlanVersion(BaseModel):
    """
    Immutable version specification for ExecutionPlan serialization formats.
    """
    model_config = ConfigDict(frozen=True)

    plan_schema_version: str = Field(default="1.0.0", description="Execution plan schema version string")
    execution_operator_version: str = Field(default="1.0.0", description="Execution operator set version string")


__all__ = ["ExecutionPlanVersion"]
