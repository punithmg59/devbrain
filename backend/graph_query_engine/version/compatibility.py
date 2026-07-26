"""
Version Compatibility Matrix Contract.

Contract for determining cross-version schema and engine compatibility.
"""

from typing import Protocol


class IVersionCompatibilityMatrix(Protocol):
    """
    Contract for validating cross-version snapshot compatibility matrix.
    """

    def is_snapshot_readable(self, snapshot_schema_version: int) -> bool:
        """Determines if a graph snapshot can be read by current query engine."""
        ...


__all__ = ["IVersionCompatibilityMatrix"]
