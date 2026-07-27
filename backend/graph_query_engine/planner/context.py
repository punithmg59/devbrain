"""
Immutable PlannerContext Object Passed Through Every Planner Stage.
"""

from typing import Any, Mapping, Optional
from pydantic import BaseModel, ConfigDict, Field

from graph_query_engine.planner.config import PlannerConfiguration, PlanningBudget
from graph_query_engine.planner.diagnostics import PlannerDiagnostics
from graph_query_engine.planner.state import PlannerState


class PlannerContext(BaseModel):
    """
    Immutable stage context object passed through every planner stage.
    Must NOT contain GraphView or graph data.
    """
    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    session_id: str = Field(..., description="Unique session identifier string")
    correlation_id: str = Field(default="", description="Correlation ID for distributed tracing")
    query_metadata: Mapping[str, Any] = Field(default_factory=dict, description="Immutable query metadata dictionary")
    configuration: PlannerConfiguration = Field(default_factory=PlannerConfiguration, description="PlannerConfiguration model")
    budget: PlanningBudget = Field(default_factory=PlanningBudget, description="PlanningBudget model")
    diagnostics: PlannerDiagnostics = Field(default_factory=PlannerDiagnostics, description="PlannerDiagnostics collector reference")
    snapshot_metadata_ref: Mapping[str, str] = Field(default_factory=dict, description="Immutable snapshot metadata references")
    index_metadata_ref: Mapping[str, str] = Field(default_factory=dict, description="Immutable index metadata references")
    planning_options: Mapping[str, Any] = Field(default_factory=dict, description="Planning options key-value pairs")
    planner_state: PlannerState = Field(default=PlannerState.CREATED, description="Current PlannerState lifecycle enum")

    @property
    def current_state(self) -> str:
        """IGraphView / contract property implementation."""
        return self.planner_state.value


__all__ = ["PlannerContext"]
