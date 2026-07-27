"""
PlannerState Enum for Planner Lifecycle State Progression.
"""

from enum import StrEnum


class PlannerState(StrEnum):
    """
    Lifecycle state enumeration for Query Planner requests.
    """
    CREATED = "CREATED"
    INITIALIZED = "INITIALIZED"
    VALIDATING = "VALIDATING"
    PLANNING = "PLANNING"
    OPTIMIZING = "OPTIMIZING"
    BUILDING_PLAN = "BUILDING_PLAN"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    TIMEOUT = "TIMEOUT"

    @property
    def is_terminal(self) -> bool:
        """Returns True if the state represents a final terminal state."""
        return self in (
            PlannerState.COMPLETED,
            PlannerState.FAILED,
            PlannerState.CANCELLED,
            PlannerState.TIMEOUT,
        )


__all__ = ["PlannerState"]
