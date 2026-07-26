"""
Query Pipeline and Executor Interface Contracts.

CONTRACT ONLY - DO NOT IMPLEMENT IN STEP 1.1.
"""

from typing import Any, Protocol


class IQueryPipeline(Protocol):
    """
    Contract for query transformation, planning, optimization, and execution pipeline.
    """

    def execute_query(self, query_ast: Any, context: Any) -> Any:
        """Executes a query AST against the graph engine context."""
        ...


class IQueryExecutor(Protocol):
    """
    Contract for low-level query step execution.
    """

    def execute_step(self, step_plan: Any, context: Any) -> Any:
        """Executes an individual physical query execution step."""
        ...


__all__ = ["IQueryPipeline", "IQueryExecutor"]
