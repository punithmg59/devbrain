"""
AlertPolicy model and AlertManager implementation.
"""

import time
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass(frozen=True)
class AlertPolicy:
    """Immutable alert threshold policy."""

    latency_threshold_ms: float = 1000.0
    memory_threshold_ratio: float = 0.90
    storage_threshold_ratio: float = 0.90
    error_threshold_count: int = 5


@dataclass(frozen=True)
class AlertEvent:
    """Immutable alert event object."""

    alert_id: str
    severity: str
    message: str
    component: str
    timestamp: float = field(default_factory=time.time)


class AlertManager:
    """Alert manager evaluating policies and generating alert events."""

    def __init__(self, policy: Optional[AlertPolicy] = None):
        self.policy = policy or AlertPolicy()
        self._alerts: List[AlertEvent] = []

    def raise_alert(self, severity: str, message: str, component: str) -> AlertEvent:
        """Raise an alert event."""
        alert = AlertEvent(
            alert_id=f"alt_{len(self._alerts) + 1}",
            severity=severity,
            message=message,
            component=component,
            timestamp=time.time(),
        )
        self._alerts.append(alert)
        return alert

    def evaluate_latency(self, latency_ms: float, operation: str) -> Optional[AlertEvent]:
        """Evaluate operation latency against policy threshold."""
        if latency_ms > self.policy.latency_threshold_ms:
            return self.raise_alert(
                severity="WARNING",
                message=f"Operation '{operation}' latency ({latency_ms:.2f}ms) exceeded threshold ({self.policy.latency_threshold_ms:.2f}ms)",
                component=operation,
            )
        return None

    def get_active_alerts(self) -> List[AlertEvent]:
        """Return list of generated alerts."""
        return list(self._alerts)
