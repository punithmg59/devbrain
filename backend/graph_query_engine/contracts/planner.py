"""
Query Planner Contract.

CONTRACT ONLY - DO NOT IMPLEMENT IN STEP 1.1.
"""

from typing import Any, Protocol


class IQueryPlanner(Protocol):
    """
    Contract for parsing logical queries and building optimized physical query plans.
    """

    def create_plan(self, query_spec: Any) -> Any:
        """Translates query specification into a physical execution plan."""
        ...


__all__ = ["IQueryPlanner"]
