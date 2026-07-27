# backend/graph_query_engine/traversal/operators/transform.py
"""Transformation, filtering, aggregation, and result building operators.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from pydantic import Field

from .base import TraversalOperator
from ..context import TraversalExecutionContext
from ..result import TraversalResult
from ..metrics import TraversalMetrics


class TraversalLimitOperator(TraversalOperator):
    """Restricts node collection to a maximum limit."""

    limit: int = Field(100, description="Max items count")

    @property
    def operator_name(self) -> str:
        return "TraversalLimit"

    def execute(
        self,
        context: TraversalExecutionContext,
        input_nodes: List[str],
        **kwargs: Any,
    ) -> List[str]:
        result = input_nodes[: self.limit]
        context.diagnostics.record_info("Operator", f"TraversalLimit truncated from {len(input_nodes)} to {len(result)}")
        return result


class TraversalSortOperator(TraversalOperator):
    """Sorts node IDs lexicographically or by custom key."""

    reverse: bool = Field(False, description="Sort order descending if True")

    @property
    def operator_name(self) -> str:
        return "TraversalSort"

    def execute(
        self,
        context: TraversalExecutionContext,
        input_nodes: List[str],
        **kwargs: Any,
    ) -> List[str]:
        result = sorted(input_nodes, reverse=self.reverse)
        context.diagnostics.record_info("Operator", f"TraversalSort sorted {len(result)} nodes")
        return result


class TraversalDeduplicateOperator(TraversalOperator):
    """Deduplicates node IDs while preserving order."""

    @property
    def operator_name(self) -> str:
        return "TraversalDeduplicate"

    def execute(
        self,
        context: TraversalExecutionContext,
        input_nodes: List[str],
        **kwargs: Any,
    ) -> List[str]:
        seen = set()
        deduped = []
        for n in input_nodes:
            if n not in seen:
                seen.add(n)
                deduped.append(n)
        context.diagnostics.record_info("Operator", f"TraversalDeduplicate reduced {len(input_nodes)} to {len(deduped)}")
        return deduped


class TraversalAggregateOperator(TraversalOperator):
    """Aggregates metrics and counts over the node stream."""

    @property
    def operator_name(self) -> str:
        return "TraversalAggregate"

    def execute(
        self,
        context: TraversalExecutionContext,
        input_nodes: List[str],
        **kwargs: Any,
    ) -> List[str]:
        count = len(input_nodes)
        context.diagnostics.record_info("Operator", f"TraversalAggregate calculated node count: {count}")
        return input_nodes


class TraversalProjectOperator(TraversalOperator):
    """Projects specific node IDs or extracts fields."""

    prefix: Optional[str] = Field(None, description="Optional node ID prefix filter")

    @property
    def operator_name(self) -> str:
        return "TraversalProject"

    def execute(
        self,
        context: TraversalExecutionContext,
        input_nodes: List[str],
        **kwargs: Any,
    ) -> List[str]:
        if self.prefix:
            projected = [n for n in input_nodes if n.startswith(self.prefix)]
        else:
            projected = list(input_nodes)
        context.diagnostics.record_info("Operator", f"TraversalProject retained {len(projected)} nodes")
        return projected


class TraversalCollectOperator(TraversalOperator):
    """Collects node stream into an accumulated list."""

    @property
    def operator_name(self) -> str:
        return "TraversalCollect"

    def execute(
        self,
        context: TraversalExecutionContext,
        input_nodes: List[str],
        **kwargs: Any,
    ) -> List[str]:
        collected = list(input_nodes)
        context.diagnostics.record_info("Operator", f"TraversalCollect collected {len(collected)} nodes")
        return collected


class TraversalResultBuilderOperator(TraversalOperator):
    """Assembles final TraversalResult object from input nodes."""

    root_nodes: List[str] = Field(default_factory=list)

    @property
    def operator_name(self) -> str:
        return "TraversalResultBuilder"

    def execute(
        self,
        context: TraversalExecutionContext,
        input_nodes: List[str],
        **kwargs: Any,
    ) -> List[str]:
        # Helper operator step returning node list
        return input_nodes

    def build_result(
        self,
        context: TraversalExecutionContext,
        nodes: List[str],
        elapsed_ms: float = 0.0,
    ) -> TraversalResult:
        metrics = TraversalMetrics(
            nodes_visited=len(nodes),
            execution_duration_ms=elapsed_ms,
        )
        return TraversalResult(
            visited_nodes=nodes,
            root_nodes=self.root_nodes,
            leaf_nodes=nodes,
            metrics=metrics,
            diagnostics_summary=context.diagnostics.summary(),
            execution_time_ms=elapsed_ms,
        )


__all__ = [
    "TraversalLimitOperator",
    "TraversalSortOperator",
    "TraversalDeduplicateOperator",
    "TraversalAggregateOperator",
    "TraversalProjectOperator",
    "TraversalCollectOperator",
    "TraversalResultBuilderOperator",
]
