"""
Exception definitions for Graph Storage module.
"""


class GraphStorageError(Exception):
    """Base exception for all Graph Storage operations."""
    pass


class TransactionError(GraphStorageError):
    """Raised when a transaction or lease operation fails in Graph Storage."""
    pass
