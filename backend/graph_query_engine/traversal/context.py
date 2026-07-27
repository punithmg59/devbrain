# backend/graph_query_engine/traversal/context.py
"""Execution context for graph traversal algorithms and operators.
"""

from __future__ import annotations

from typing import Any, Dict, Optional, Set
from pydantic import BaseModel, Field, ConfigDict

from .diagnostics import TraversalDiagnostics
from .metrics import TraversalMetrics


class TraversalLimits(BaseModel):
    """Immutable execution boundaries for graph traversals."""

    model_config = ConfigDict(frozen=True)

    max_depth: int = Field(100, description="Maximum traversal depth")
    max_nodes: int = Field(10000, description="Maximum total nodes to visit")
    max_edges: int = Field(50000, description="Maximum total edges to traverse")
    timeout_ms: float = Field(30000.0, description="Execution timeout in milliseconds")
    direction: str = Field("OUTGOING", description="Traversal direction: OUTGOING, INCOMING, BOTH")


class TraversalExecutionContext(BaseModel):
    """Execution context carrying graph view, index layer, limits, and runtime stats."""

    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    graph_view: Any = Field(..., description="Immutable GraphView instance")
    index_layer: Optional[Any] = Field(None, description="Optional IndexLayer for fast lookups")
    limits: TraversalLimits = Field(default_factory=TraversalLimits)
    diagnostics: TraversalDiagnostics = Field(default_factory=TraversalDiagnostics)
    metrics: TraversalMetrics = Field(default_factory=TraversalMetrics)
    custom_params: Dict[str, Any] = Field(default_factory=dict)


__all__ = ["TraversalLimits", "TraversalExecutionContext"]
