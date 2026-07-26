"""
HealthReport model and HealthMonitor implementation.
"""

import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass(frozen=True)
class HealthReport:
    """Immutable health status report."""

    overall_health: str  # "HEALTHY", "DEGRADED", "UNHEALTHY"
    component_health: Dict[str, str] = field(default_factory=dict)
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    timestamp: float = field(default_factory=time.time)


class HealthMonitor:
    """Subsystem health monitor inspecting storage components."""

    def __init__(self):
        self._components: Dict[str, str] = {
            "storage": "HEALTHY",
            "cache": "HEALTHY",
            "transactions": "HEALTHY",
            "partitions": "HEALTHY",
            "snapshots": "HEALTHY",
        }

    def set_component_health(self, component_name: str, status: str) -> None:
        self._components[component_name] = status

    def check_storage(self) -> str:
        return self._components.get("storage", "HEALTHY")

    def check_cache(self) -> str:
        return self._components.get("cache", "HEALTHY")

    def check_transactions(self) -> str:
        return self._components.get("transactions", "HEALTHY")

    def check_partitions(self) -> str:
        return self._components.get("partitions", "HEALTHY")

    def check_snapshots(self) -> str:
        return self._components.get("snapshots", "HEALTHY")

    def overall_status(self) -> str:
        statuses = set(self._components.values())
        if "UNHEALTHY" in statuses:
            return "UNHEALTHY"
        elif "DEGRADED" in statuses:
            return "DEGRADED"
        return "HEALTHY"

    def check_health(self) -> HealthReport:
        return self.generate_report()

    def generate_report(self) -> HealthReport:
        overall = self.overall_status()
        warnings = []
        errors = []
        recommendations = []

        if overall == "DEGRADED":
            warnings.append("One or more components are reporting DEGRADED status")
            recommendations.append("Inspect component metrics and logs")
        elif overall == "UNHEALTHY":
            errors.append("One or more components are UNHEALTHY")
            recommendations.append("Perform immediate system diagnostics")

        return HealthReport(
            overall_health=overall,
            component_health=dict(self._components),
            warnings=warnings,
            errors=errors,
            recommendations=recommendations,
            timestamp=time.time(),
        )
