# backend/graph_query_engine/traversal/operators/base.py
"""Abstract base class for composable traversal operators.
"""

from __future__ import annotations

import abc
from typing import Any, List
from pydantic import BaseModel, ConfigDict

from ..context import TraversalExecutionContext
from ..result import TraversalResult


class TraversalOperator(BaseModel, abc.ABC):
    """Abstract composable traversal operator."""

    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    @property
    @abc.abstractmethod
    def operator_name(self) -> str:
        """Name of the traversal operator."""

    @abc.abstractmethod
    def execute(
        self,
        context: TraversalExecutionContext,
        input_nodes: List[str],
        **kwargs: Any,
    ) -> List[str]:
        """Executes operator logic and returns modified list of node IDs."""


__all__ = ["TraversalOperator"]
