"""
IsolationLevel enum and IsolationPolicy model.
"""

from dataclasses import dataclass
from enum import Enum


class IsolationLevel(Enum):
    READ_COMMITTED = "READ_COMMITTED"
    REPEATABLE_READ = "REPEATABLE_READ"
    SNAPSHOT_ISOLATION = "SNAPSHOT_ISOLATION"
    SERIALIZABLE = "SERIALIZABLE"


@dataclass(frozen=True)
class IsolationPolicy:
    """Immutable isolation policy configuration."""

    level: IsolationLevel = IsolationLevel.READ_COMMITTED
    lock_timeout_seconds: float = 5.0
    allow_phantom_reads: bool = False
    allow_dirty_reads: bool = False
