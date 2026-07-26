"""
RebalancePlan and MigrationStep models.
"""

from dataclasses import dataclass
from typing import List


@dataclass(frozen=True)
class MigrationStep:
    """Single step in a rebalance plan."""

    source_partition_id: str
    target_partition_id: str
    segment_id: str
    size_bytes: int


@dataclass(frozen=True)
class RebalancePlan:
    """Structured plan for rebalancing partitions."""

    steps: List[MigrationStep]
    estimated_cost_seconds: float
    estimated_benefit_ratio: float
    validation_result: bool
    description: str
