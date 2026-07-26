"""
TransactionMetrics model definition.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class TransactionMetrics:
    """Immutable telemetry metrics for the Transaction Engine."""

    active_transactions: int
    commits: int
    rollbacks: int
    aborts: int
    average_commit_time_ms: float
    average_rollback_time_ms: float
    lock_wait_time_ms: float
    conflict_count: int
