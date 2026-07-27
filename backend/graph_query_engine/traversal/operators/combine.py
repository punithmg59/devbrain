# backend/graph_query_engine/traversal/operators/combine.py
"""TraversalMerge, TraversalUnion, and TraversalIntersection operators.
"""

from __future__ import annotations

from typing import Any, List
from pydantic import Field

from .base import TraversalOperator
from ..context import TraversalExecutionContext


class TraversalMergeOperator(TraversalOperator):
    """Merges input nodes with secondary node stream maintaining order."""

    secondary_nodes: List[str] = Field(default_factory=list)

    @property
    def operator_name(self) -> str:
        return "TraversalMerge"

    def execute(
        self,
        context: TraversalExecutionContext,
        input_nodes: List[str],
        **kwargs: Any,
    ) -> List[str]:
        merged = list(input_nodes) + list(self.secondary_nodes)
        context.diagnostics.record_info("Operator", f"TraversalMerge merged to {len(merged)} nodes")
        return merged


class TraversalUnionOperator(TraversalOperator):
    """Set union of input node stream and secondary stream."""

    secondary_nodes: List[str] = Field(default_factory=list)

    @property
    def operator_name(self) -> str:
        return "TraversalUnion"

    def execute(
        self,
        context: TraversalExecutionContext,
        input_nodes: List[str],
        **kwargs: Any,
    ) -> List[str]:
        s1 = set(input_nodes)
        s2 = set(self.secondary_nodes)
        result = list(s1.union(s2))
        context.diagnostics.record_info("Operator", f"TraversalUnion yielded {len(result)} unique nodes")
        return result


class TraversalIntersectionOperator(TraversalOperator):
    """Set intersection of input node stream and secondary stream."""

    secondary_nodes: List[str] = Field(default_factory=list)

    @property
    def operator_name(self) -> str:
        return "TraversalIntersection"

    def execute(
        self,
        context: TraversalExecutionContext,
        input_nodes: List[str],
        **kwargs: Any,
    ) -> List[str]:
        s1 = set(input_nodes)
        s2 = set(self.secondary_nodes)
        result = list(s1.intersection(s2))
        context.diagnostics.record_info("Operator", f"TraversalIntersection yielded {len(result)} common nodes")
        return result


__all__ = [
    "TraversalMergeOperator",
    "TraversalUnionOperator",
    "TraversalIntersectionOperator",
]
