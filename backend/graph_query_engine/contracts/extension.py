"""
Extension Protocol Definitions.

CONTRACT ONLY - DO NOT IMPLEMENT IN STEP 1.1.
"""

from typing import Any, Protocol


class IQueryExtension(Protocol):
    """
    Contract for user-defined graph query extensions or functions.
    """

    def invoke(self, *args: Any, **kwargs: Any) -> Any:
        """Invokes extension capability."""
        ...


__all__ = ["IQueryExtension"]
