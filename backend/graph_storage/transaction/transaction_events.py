"""
Transaction event model interfaces.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class TransactionStartedEvent:
    transaction_id: str
    isolation_level: str
    start_time_epoch_sec: float


@dataclass(frozen=True)
class TransactionCommittedEvent:
    transaction_id: str
    commit_time_epoch_sec: float


@dataclass(frozen=True)
class TransactionRolledBackEvent:
    transaction_id: str
    reason: str
    rollback_time_epoch_sec: float


@dataclass(frozen=True)
class TransactionAbortedEvent:
    transaction_id: str
    reason: str
    abort_time_epoch_sec: float


@dataclass(frozen=True)
class TransactionRecoveredEvent:
    transaction_id: str
    state: str


@dataclass(frozen=True)
class LockAcquiredEvent:
    transaction_id: str
    key: str
    lock_type: str


@dataclass(frozen=True)
class LockReleasedEvent:
    transaction_id: str
    key: str


@dataclass(frozen=True)
class ConflictDetectedEvent:
    transaction_id: str
    conflicting_key: str
    conflict_type: str
