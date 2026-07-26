"""
PartitionPlacementResult model definition.
"""

from dataclasses import dataclass
from graph_storage.model import PartitionId


@dataclass(frozen=True)
class PartitionPlacementResult:
    """Immutable result object from placement engine selection."""

    target_partition_id: PartitionId
    planner_name: str
    reason: str
    confidence_score: float
    estimated_utilization_ratio: float
    policy_name: str
