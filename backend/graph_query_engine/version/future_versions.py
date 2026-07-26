"""
Future Version Strategy Placeholder.

Placeholder for future schema migration and forward compatibility strategies.
"""

from typing import Protocol


class IFutureVersionStrategy(Protocol):
    """
    Contract for handling forward-compatibility strategies for future graph storage schemas.
    """

    def handle_unsupported_version(self, version_number: int) -> None:
        """Handles unsupported schema versions."""
        ...


__all__ = ["IFutureVersionStrategy"]
