"""
CapacityModel model definition.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class CapacityModel:
    """Immutable domain model representing partition capacity metrics and forecasts."""

    capacity_bytes: int
    available_bytes: int
    utilization_ratio: float
    growth_rate_bytes_per_sec: float
    forecast_days_until_full: float
    headroom_bytes: int
