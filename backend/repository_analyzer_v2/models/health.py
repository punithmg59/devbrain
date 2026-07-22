from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class HealthStatus(str, Enum):
    """Overall status indicator for subsystems and the overall system."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


class ComponentHealth(BaseModel):
    """Health check outcome for an individual component/subsystem."""
    name: str = Field(..., description="Name of the subsystem component")
    status: HealthStatus = Field(default=HealthStatus.HEALTHY, description="Component health status")
    duration_ms: float = Field(default=0.0, ge=0.0, description="Duration of the check in milliseconds")
    warnings: List[str] = Field(default_factory=list, description="Non-fatal warnings recorded")
    errors: List[str] = Field(default_factory=list, description="Fatal or error conditions recorded")
    details: Dict[str, Any] = Field(default_factory=dict, description="Arbitrary component metadata")


class HealthReport(BaseModel):
    """Complete aggregated system health report."""
    status: HealthStatus = Field(default=HealthStatus.HEALTHY, description="Aggregated overall status")
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Timestamp when report was generated",
    )
    total_duration_ms: float = Field(default=0.0, ge=0.0, description="Total duration of all health checks")
    components: List[ComponentHealth] = Field(default_factory=list, description="Health status of all components")
    warnings: List[str] = Field(default_factory=list, description="Aggregated system warnings")
    errors: List[str] = Field(default_factory=list, description="Aggregated system errors")
