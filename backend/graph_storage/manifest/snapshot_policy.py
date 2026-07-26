"""
SnapshotPolicy model definition for snapshot retention and maintenance rules.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class SnapshotPolicy:
    """Immutable policy configuration abstraction for snapshot retention and maintenance."""

    maximum_history: int = 50
    retention_period_seconds: float = 2592000.0  # 30 days
    pinning_enabled: bool = True
    cleanup_policy: str = "retain_pinned"
    expiration_policy: str = "expire_by_age"
