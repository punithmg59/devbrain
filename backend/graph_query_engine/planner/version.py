"""
PlannerVersion Object for Query Planner Generation and Semver Metadata.
"""

from typing import Self
from pydantic import BaseModel, ConfigDict, Field


class PlannerVersion(BaseModel):
    """
    Immutable representation of Planner versioning and generation.
    """
    model_config = ConfigDict(frozen=True)

    major: int = Field(default=4, ge=0, description="Major version integer")
    minor: int = Field(default=1, ge=0, description="Minor version integer")
    patch: int = Field(default=0, ge=0, description="Patch version integer")
    planner_generation: int = Field(default=1, ge=1, description="Planner engine generation")
    compatibility_version: str = Field(default="4.0.0", description="Semver lower compatibility bound")

    def __str__(self) -> str:
        return f"{self.major}.{self.minor}.{self.patch}-gen{self.planner_generation}"

    def is_compatible_with(self, target_version: str) -> bool:
        """Returns True if planner is compatible with target_version string."""
        return str(target_version).startswith(str(self.major))


__all__ = ["PlannerVersion"]
