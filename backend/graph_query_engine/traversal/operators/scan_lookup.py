# backend/graph_query_engine/traversal/operators/scan_lookup.py
"""NodeScan and IndexLookup traversal operators.
"""

from __future__ import annotations

from typing import Any, List, Optional
from pydantic import Field

from .base import TraversalOperator
from ..context import TraversalExecutionContext


class NodeScanOperator(TraversalOperator):
    """Operator that scans nodes from GraphView."""

    node_type: Optional[str] = Field(None, description="Optional node type filter")

    @property
    def operator_name(self) -> str:
        return "NodeScan"

    def execute(
        self,
        context: TraversalExecutionContext,
        input_nodes: List[str],
        **kwargs: Any,
    ) -> List[str]:
        gv = context.graph_view
        nodes: List[str] = []

        if hasattr(gv, "get_all_nodes"):
            raw = gv.get_all_nodes()
            nodes = list(raw)
        elif hasattr(gv, "nodes"):
            nodes = list(gv.nodes)
        elif isinstance(gv, dict):
            nodes = list(gv.keys())

        if self.node_type and hasattr(gv, "get_node_type"):
            nodes = [n for n in nodes if gv.get_node_type(n) == self.node_type]

        context.diagnostics.record_info("Operator", f"NodeScan produced {len(nodes)} nodes")
        return nodes


class IndexLookupOperator(TraversalOperator):
    """Operator that looks up node IDs via IndexLayer."""

    index_name: str = Field(..., description="Name of the lookup index")
    key: Any = Field(..., description="Lookup key or term")

    @property
    def operator_name(self) -> str:
        return "IndexLookup"

    def execute(
        self,
        context: TraversalExecutionContext,
        input_nodes: List[str],
        **kwargs: Any,
    ) -> List[str]:
        index = context.index_layer
        results: List[str] = []

        if index is not None and hasattr(index, "lookup"):
            raw = index.lookup(self.index_name, self.key)
            if isinstance(raw, (list, set, tuple)):
                results = [str(x) for x in raw]
            elif raw is not None:
                results = [str(raw)]
            context.diagnostics.record_cache_hit()
        else:
            context.diagnostics.record_cache_miss()
            # Fallback to scanning graph view
            results = input_nodes

        context.diagnostics.record_info("Operator", f"IndexLookup('{self.index_name}') found {len(results)} matches")
        return results


__all__ = ["NodeScanOperator", "IndexLookupOperator"]
