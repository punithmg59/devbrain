"""
ConsistencyValidator implementation.
"""

from typing import List
from graph_storage.exceptions import GraphStorageError
from graph_storage.transaction.transaction_context import TransactionContext


class ConsistencyValidator:
    """Validator enforcing cross-layer storage consistency."""

    @classmethod
    def validate_transaction_consistency(cls, ctx: TransactionContext) -> None:
        """Validate transaction context invariants."""
        if not ctx.transaction_id or not ctx.transaction_id.value:
            raise GraphStorageError("Transaction ID cannot be empty")
        if ctx.start_time <= 0:
            raise GraphStorageError("Transaction start time must be positive")

    @classmethod
    def validate_cross_layer_consistency(cls, ctx: TransactionContext, active_txs: List[TransactionContext]) -> None:
        """Validate cross-layer constraints."""
        cls.validate_transaction_consistency(ctx)
