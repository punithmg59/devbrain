"""
LogicalPlan Versioning Model.
"""

from pydantic import BaseModel, ConfigDict, Field


class LogicalPlanVersion(BaseModel):
    """
    Immutable versioning model for LogicalPlan schema and operator definitions.
    """
    model_config = ConfigDict(frozen=True)

    plan_schema_version: str = Field(default="1.0.0", description="LogicalPlan schema version")
    operator_version: str = Field(default="1.0.0", description="Logical operator definitions version")

    def is_compatible_with(self, target_version: str) -> bool:
        """Verifies major version compatibility."""
        target_major = target_version.split(".")[0]
        schema_major = self.plan_schema_version.split(".")[0]
        return target_major == schema_major

    def __str__(self) -> str:
        return f"plan_v{self.plan_schema_version}:op_v{self.operator_version}"


__all__ = ["LogicalPlanVersion"]
