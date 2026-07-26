"""
Query Validation Protocols.

CONTRACT ONLY - DO NOT IMPLEMENT IN STEP 1.1.
"""

from typing import Any, Protocol


class IQueryValidator(Protocol):
    """
    Contract for semantic validation of input queries prior to execution planning.
    """

    def validate(self, query: Any) -> None:
        """Validates query model. Raises ValidationError if invalid."""
        ...


__all__ = ["IQueryValidator"]
