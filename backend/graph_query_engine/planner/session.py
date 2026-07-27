"""
PlannerSession Representing One Planning Request Session.
"""

from datetime import datetime, timezone
import uuid
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field

from graph_query_engine.planner.lifecycle import PlannerLifecycle
from graph_query_engine.planner.state import PlannerState
from graph_query_engine.planner.version import PlannerVersion


class PlannerSession(BaseModel):
    """
    Representation of an active planning session request.
    """
    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    session_id: str = Field(
        default_factory=lambda: f"psess_{uuid.uuid4().hex[:12]}",
        description="Unique planner session identifier string",
    )
    correlation_id: str = Field(
        default_factory=lambda: f"corr_{uuid.uuid4().hex[:12]}",
        description="Correlation ID for distributed tracing",
    )
    version: PlannerVersion = Field(default_factory=PlannerVersion, description="PlannerVersion instance")
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="UTC creation timestamp",
    )

    def create_lifecycle(self) -> PlannerLifecycle:
        """Instantiates a new PlannerLifecycle initialized to CREATED."""
        return PlannerLifecycle(initial_state=PlannerState.CREATED)


__all__ = ["PlannerSession"]
