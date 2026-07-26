"""
TransactionContext model definition.
"""

from dataclasses import dataclass, field
from typing import Dict, Optional

from graph_storage.model import TransactionId
from graph_storage.transaction.isolation_policy import IsolationLevel
from graph_storage.transaction.transaction_sets import ReadSet, WriteSet
from graph_storage.transaction.transaction_state import TransactionState


@dataclass(frozen=True)
class TransactionContext:
    """Immutable transaction context."""

    transaction_id: TransactionId
    start_time: float
    status: TransactionState
    isolation_level: IsolationLevel
    read_set: ReadSet
    write_set: WriteSet
    metadata: Dict[str, str] = field(default_factory=dict)
    parent_transaction_id: Optional[TransactionId] = None
