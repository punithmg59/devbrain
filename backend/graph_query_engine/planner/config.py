"""
PlannerConfiguration and PlanningBudget Models.
"""

from typing import Optional
from pydantic import BaseModel, ConfigDict, Field

from graph_query_engine.errors import InvalidPlannerConfigError


class PlanningBudget(BaseModel):
    """
    Immutable planning budget limits configuration.
    """
    model_config = ConfigDict(frozen=True)

    timeout_seconds: float = Field(default=30.0, gt=0.0, description="Maximum planning timeout in seconds")
    max_planning_stages: int = Field(default=10, gt=0, description="Maximum allowed planning pipeline stages")
    max_optimization_iterations: int = Field(default=100, gt=0, description="Maximum optimization rule passes")
    max_planner_memory_bytes: int = Field(default=104_857_600, gt=0, description="Max RAM allowed for planning (100MB default)")
    max_operator_count: int = Field(default=1000, gt=0, description="Maximum logical/physical operator count limit")
    max_estimated_cost: float = Field(default=1_000_000.0, gt=0.0, description="Maximum allowed plan cost limit")

    def validate_budget(self) -> None:
        """
        Validates budget limits. Raises InvalidPlannerConfigError if invalid.
        """
        if self.timeout_seconds <= 0:
            raise InvalidPlannerConfigError("PlanningBudget timeout_seconds must be positive.")
        if self.max_planning_stages <= 0:
            raise InvalidPlannerConfigError("PlanningBudget max_planning_stages must be positive.")


class PlannerConfiguration(BaseModel):
    """
    Immutable planner behavior configuration flags and limits.
    """
    model_config = ConfigDict(frozen=True)

    optimization_enabled: bool = Field(default=True, description="Enable plan optimization rules")
    diagnostics_enabled: bool = Field(default=True, description="Enable detailed diagnostic event logging")
    cost_estimation_enabled: bool = Field(default=True, description="Enable cost model estimation")
    validation_enabled: bool = Field(default=True, description="Enable plan validation rules")
    debug_mode: bool = Field(default=False, description="Enable debug trace collection")
    strict_mode: bool = Field(default=False, description="Fail immediately on non-critical warnings")
    budget: PlanningBudget = Field(default_factory=PlanningBudget, description="Associated PlanningBudget model")


__all__ = [
    "PlanningBudget",
    "PlannerConfiguration",
]
