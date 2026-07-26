"""
SecurityMetrics model definition.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class SecurityMetrics:
    """Immutable telemetry metrics for the Security Subsystem."""

    authentication_count: int
    authorization_count: int
    denied_requests: int
    audit_entries: int
    permission_checks: int
    security_violations: int
    integrity_failures: int
