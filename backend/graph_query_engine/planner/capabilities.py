"""
PlannerCapabilities Registry for Feature Advertisements.
"""

from enum import StrEnum
from pydantic import BaseModel, ConfigDict, Field

from graph_query_engine.errors import CapabilityUnsupportedError


class CapabilityFlag(StrEnum):
    """Enumeration of Query Planner capabilities."""
    LOGICAL_PLANNING = "LOGICAL_PLANNING"
    COST_ESTIMATION = "COST_ESTIMATION"
    OPTIMIZATION = "OPTIMIZATION"
    PHYSICAL_PLANNING = "PHYSICAL_PLANNING"
    EXECUTION_PLAN = "EXECUTION_PLAN"
    GRAPH_DIFF = "GRAPH_DIFF"
    BLAST_RADIUS = "BLAST_RADIUS"
    DISTRIBUTED_PLANNING = "DISTRIBUTED_PLANNING"


class PlannerCapabilities(BaseModel):
    """
    Immutable capability registry advertising supported planner feature flags.
    """
    model_config = ConfigDict(frozen=True)

    supported_capabilities: tuple[CapabilityFlag, ...] = Field(
        default_factory=lambda: (
            CapabilityFlag.LOGICAL_PLANNING,
            CapabilityFlag.COST_ESTIMATION,
            CapabilityFlag.OPTIMIZATION,
        ),
        description="Tuple of supported CapabilityFlag items",
    )

    def is_supported(self, feature: str | CapabilityFlag) -> bool:
        """Returns True if feature is present in supported_capabilities."""
        feat_str = feature.value if isinstance(feature, CapabilityFlag) else str(feature).upper()
        return any(c.value == feat_str for c in self.supported_capabilities)

    def require_capability(self, feature: str | CapabilityFlag) -> None:
        """
        Ensures feature is supported. Raises CapabilityUnsupportedError if missing.
        """
        if not self.is_supported(feature):
            raise CapabilityUnsupportedError(f"Requested planner capability '{feature}' is not supported.")

    def list_capabilities(self) -> tuple[str, ...]:
        """Returns tuple of capability strings."""
        return tuple(c.value for c in self.supported_capabilities)


__all__ = [
    "CapabilityFlag",
    "PlannerCapabilities",
]
