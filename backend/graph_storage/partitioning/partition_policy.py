"""
PartitionPolicy model definition for partition management rules.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class PartitionPolicy:
    """Immutable policy configuration for partition sizing and placement rules."""

    maximum_partition_size_bytes: int = 1073741824  # 1 GB default
    target_utilization_ratio: float = 0.80
    growth_threshold_ratio: float = 0.85
    rebalance_threshold_ratio: float = 0.90
    placement_policy: str = "default"
    replication_policy: str = "none"
