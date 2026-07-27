"""
PlannerMetrics Model and MetricsCollector.
"""

from datetime import datetime, timezone
import threading
from pydantic import BaseModel, ConfigDict, Field


class PlannerMetrics(BaseModel):
    """
    Immutable telemetry metrics snapshot for Query Planner operations.
    """
    model_config = ConfigDict(frozen=True)

    planning_time_seconds: float = Field(default=0.0, ge=0.0, description="Total planning duration in seconds")
    stage_durations_ms: dict[str, float] = Field(default_factory=dict, description="Mapping of stage_name -> duration_ms")
    optimization_count: int = Field(default=0, ge=0, description="Total optimization attempts count")
    validation_count: int = Field(default=0, ge=0, description="Total validation passes count")
    warning_count: int = Field(default=0, ge=0, description="Total warnings recorded count")
    error_count: int = Field(default=0, ge=0, description="Total errors recorded count")
    recorded_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="UTC timestamp of metric snapshot creation",
    )


class MetricsCollector:
    """
    Thread-safe operational metrics collector for Planner sessions.
    """

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._planning_time: float = 0.0
        self._stage_durations: dict[str, float] = {}
        self._optimization_count: int = 0
        self._validation_count: int = 0
        self._warning_count: int = 0
        self._error_count: int = 0

    def record_stage_duration(self, stage_name: str, duration_ms: float) -> None:
        """Records planning stage duration in milliseconds."""
        with self._lock:
            self._stage_durations[stage_name] = duration_ms

    def increment_optimizations(self) -> None:
        """Increments optimization passes counter."""
        with self._lock:
            self._optimization_count += 1

    def increment_validations(self) -> None:
        """Increments validation passes counter."""
        with self._lock:
            self._validation_count += 1

    def set_total_planning_time(self, seconds: float) -> None:
        """Sets total planning duration in seconds."""
        with self._lock:
            self._planning_time = seconds

    def snapshot(self) -> PlannerMetrics:
        """Returns immutable PlannerMetrics snapshot."""
        return self.get_metrics()

    def get_metrics(self) -> PlannerMetrics:
        """Returns immutable PlannerMetrics snapshot."""
        with self._lock:
            return PlannerMetrics(
                planning_time_seconds=self._planning_time,
                stage_durations_ms=dict(self._stage_durations),
                optimization_count=self._optimization_count,
                validation_count=self._validation_count,
                warning_count=self._warning_count,
                error_count=self._error_count,
            )


__all__ = [
    "PlannerMetrics",
    "MetricsCollector",
]
