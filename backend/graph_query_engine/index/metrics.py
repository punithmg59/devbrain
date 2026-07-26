"""
Index Metrics and Telemetry Collector for Graph Query Engine.
"""

from datetime import datetime, timezone
from pydantic import BaseModel, ConfigDict, Field


class IndexMetrics(BaseModel):
    """
    Immutable telemetry metrics snapshot for the Index subsystem.
    """
    model_config = ConfigDict(frozen=True)

    registered_indexes_count: int = Field(default=0, ge=0, description="Total registered index count")
    validation_count: int = Field(default=0, ge=0, description="Total validation executions count")
    build_count: int = Field(default=0, ge=0, description="Total index build executions count")
    lookup_count_placeholder: int = Field(default=0, ge=0, description="Placeholder total lookup calls counter")
    cache_hits_placeholder: int = Field(default=0, ge=0, description="Placeholder cache hit counter")
    recorded_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="UTC timestamp of metric recording",
    )


class IndexStatisticsCollector:
    """
    Collector aggregating operational metrics over active index instances.
    """

    @classmethod
    def collect(cls, registered_count: int = 0, build_count: int = 0, validation_count: int = 0) -> IndexMetrics:
        """
        Generates immutable IndexMetrics snapshot.
        """
        return IndexMetrics(
            registered_indexes_count=registered_count,
            build_count=build_count,
            validation_count=validation_count,
        )


__all__ = [
    "IndexMetrics",
    "IndexStatisticsCollector",
]
