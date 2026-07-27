"""
Graph Adapter Contract.
"""

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class IGraphAdapter(Protocol):
    """
    Contract for transforming external graph structures into GraphView.
    """

    @classmethod
    def adapt(cls, dependency_graph: Any) -> Any:
        """Transforms a DependencyGraph model into a validated, immutable GraphView instance."""
        ...


__all__ = ["IGraphAdapter"]
