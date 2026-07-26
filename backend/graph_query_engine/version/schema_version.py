"""
Storage Schema Version Contract.

Contract for checking compatibility with Graph Storage segment schema versions.
"""

from typing import Protocol


class ISchemaVersion(Protocol):
    """
    Contract representing Graph Storage snapshot schema compatibility.
    """

    @property
    def schema_id(self) -> str:
        """Unique schema identifier."""
        ...

    @property
    def version_number(self) -> int:
        """Numeric schema revision."""
        ...

    def is_compatible_with(self, target_schema_version: int) -> bool:
        """Validates schema compatibility."""
        ...


__all__ = ["ISchemaVersion"]
