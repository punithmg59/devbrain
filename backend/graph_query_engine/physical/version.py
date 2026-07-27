"""
Physical Plan SemVer Versioning Model.
"""

from pydantic import BaseModel, ConfigDict, Field


class PhysicalPlanVersion(BaseModel):
    """
    Immutable version specification for PhysicalPlan serialization formats.
    """
    model_config = ConfigDict(frozen=True)

    plan_schema_version: str = Field(default="1.0.0", description="Physical plan schema version string")
    physical_operator_version: str = Field(default="1.0.0", description="Physical operator set version string")


__all__ = ["PhysicalPlanVersion"]
