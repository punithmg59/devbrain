"""
Query Budget Manager Interface Contract.

CONTRACT ONLY - DO NOT IMPLEMENT IN STEP 1.1.
"""

from typing import Protocol


class IQueryBudgetManager(Protocol):
    """
    Contract for monitoring and enforcing query resource budgets (time, memory, depth).
    """

    def check_budget(self) -> None:
        """
        Validates remaining budget. Raises TimeoutError or ResourceLimitExceeded if exhausted.
        """
        ...


__all__ = ["IQueryBudgetManager"]
