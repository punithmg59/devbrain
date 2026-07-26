"""
API Layer Protocols for Graph Query Engine.

CONTRACT ONLY - DO NOT IMPLEMENT IN STEP 1.1.
"""

from typing import Any, Protocol


class IQueryEngineAPI(Protocol):
    """
    High-level API entrypoint contract for executing queries against Graph Query Engine.
    """

    def query(self, query_str: str, **params: Any) -> Any:
        """Executes a query string against the engine."""
        ...


__all__ = ["IQueryEngineAPI"]
