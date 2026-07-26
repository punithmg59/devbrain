"""
Shared Common Contracts for Graph Query Engine.
"""

from typing import Any, Protocol


class Identifiable(Protocol):
    """
    Contract for objects possessing a unique string identifier.
    """

    @property
    def id(self) -> str:
        """Unique object identifier."""
        ...


class Versioned(Protocol):
    """
    Contract for objects tracking schema or snapshot versions.
    """

    @property
    def version(self) -> str:
        """Version string."""
        ...


class Validatable(Protocol):
    """
    Contract for self-validating domain models.
    """

    def validate(self) -> None:
        """
        Validates internal invariants. Raises ValidationError if invalid.
        """
        ...
