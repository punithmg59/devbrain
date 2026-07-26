"""
Index Health and Performance Reporting Models for Graph Query Engine.
"""

from datetime import datetime, timezone
from enum import StrEnum
from pydantic import BaseModel, ConfigDict, Field

from graph_query_engine.index.diagnostics import IndexDiagnostics


class HealthStatus(StrEnum):
    """Overall index health status."""
    HEALTHY = "HEALTHY"
    WARNING = "WARNING"
    FAILED = "FAILED"


class IndexHealthReport(BaseModel):
    """
    Immutable health status report for the Index subsystem.
    """
    model_config = ConfigDict(frozen=True)

    status: HealthStatus = Field(..., description="HEALTHY, WARNING, or FAILED")
    diagnostics: IndexDiagnostics = Field(..., description="Associated IndexDiagnostics model")
    errors: tuple[str, ...] = Field(default_factory=tuple, description="Error message strings")
    warnings: tuple[str, ...] = Field(default_factory=tuple, description="Warning message strings")
    recommendations: tuple[str, ...] = Field(default_factory=tuple, description="Recommended remediation steps")
    generated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="UTC timestamp of report generation",
    )


class IndexPerformanceReport(BaseModel):
    """
    Immutable structured performance summary report for an index or index set.
    """
    model_config = ConfigDict(frozen=True)

    total_indexes: int = Field(default=0, ge=0, description="Total active indexes evaluated")
    total_build_duration_seconds: float = Field(default=0.0, ge=0.0, description="Total construction duration in seconds")
    estimated_total_memory_bytes: int = Field(default=0, ge=0, description="Estimated total RAM footprint in bytes")
    lookup_complexity_summary: str = Field(default="O(1) Hash-backed / CSR-slice", description="Algorithmic complexity summary")
    registry_index_count: int = Field(default=0, ge=0, description="Registered index types count")
    generated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="UTC timestamp of report generation",
    )


__all__ = [
    "HealthStatus",
    "IndexHealthReport",
    "IndexPerformanceReport",
]
