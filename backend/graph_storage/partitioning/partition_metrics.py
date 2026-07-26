"""
PartitionMetrics model definition.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class PartitionMetrics:
    """Immutable telemetry metrics for a storage partition."""

    utilization_ratio: float
    fragmentation_ratio: float
    occupancy_ratio: float
    growth_rate_bytes_per_sec: float
    read_count: int
    write_count: int
