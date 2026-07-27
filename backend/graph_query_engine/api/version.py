"""
Public Query API Versioning.

Defines API schema version and compatibility model for the DevBrain Graph Query Engine API.
"""

from typing import Tuple
from pydantic import BaseModel, ConfigDict, Field


class QueryVersion(BaseModel):
    """Immutable Public Query API version specification model."""

    model_config = ConfigDict(frozen=True)

    major: int = Field(default=1, ge=0, description="Major API version number")
    minor: int = Field(default=0, ge=0, description="Minor API version number")
    patch: int = Field(default=0, ge=0, description="Patch API version number")
    api_schema: str = Field(default="v1.0", description="API Schema specification version tag")

    def to_tuple(self) -> Tuple[int, int, int]:
        """Returns version as (major, minor, patch) tuple."""
        return (self.major, self.minor, self.patch)

    def __str__(self) -> str:
        return f"{self.major}.{self.minor}.{self.patch}-{self.api_schema}"


__all__ = ["QueryVersion"]
