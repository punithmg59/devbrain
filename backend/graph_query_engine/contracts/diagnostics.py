"""
Query Diagnostics Interface Contract.

CONTRACT ONLY - DO NOT IMPLEMENT IN STEP 1.1.
"""

from typing import Any, Protocol


class IQueryDiagnostics(Protocol):
    """
    Contract for gathering execution profile and performance diagnostics.
    """

    def record_metric(self, name: str, value: float) -> None:
        """Records a diagnostic execution metric."""
        ...

    def get_profile(self) -> dict[str, Any]:
        """Returns diagnostic execution profile data."""
        ...


__all__ = ["IQueryDiagnostics"]
