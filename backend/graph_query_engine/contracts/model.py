"""
Query Context Contract.

CONTRACT ONLY - DO NOT IMPLEMENT IN STEP 1.1.
"""

from typing import Protocol

from graph_query_engine.types import CorrelationId, QueryId, SnapshotId


class IQueryContext(Protocol):
    """
    Contract providing context, execution budgets, and graph snapshot references during query execution.
    """

    @property
    def query_id(self) -> QueryId:
        """Unique ID of active query."""
        ...

    @property
    def snapshot_id(self) -> SnapshotId:
        """Target graph snapshot identifier."""
        ...

    @property
    def correlation_id(self) -> CorrelationId:
        """Trace correlation ID."""
        ...


__all__ = ["IQueryContext"]
