"""
Public Query API Execution Options.
"""

from typing import Any, Dict, Optional, Tuple
from pydantic import BaseModel, ConfigDict, Field


class QueryOptions(BaseModel):
    """
    Immutable Public Query API execution options container.
    """

    model_config = ConfigDict(frozen=True)

    enable_cache: bool = Field(default=True, description="Enable query caching")
    optimization_level: int = Field(default=2, ge=0, le=3, description="Planner optimization level (0=none, 3=aggressive)")
    strict_validation: bool = Field(default=True, description="Fail execution on non-fatal warnings")
    include_diagnostics: bool = Field(default=True, description="Include detailed planner and traversal diagnostics in response")
    include_statistics: bool = Field(default=True, description="Include timing and metric statistics in response")
    custom_flags: Dict[str, Any] = Field(default_factory=dict, description="Arbitrary extension flags")


__all__ = ["QueryOptions"]
