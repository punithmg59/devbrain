# backend/graph_query_engine/traversal/result.py
"""Immutable result model for graph traversals and path exploration.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, ConfigDict

from .metrics import TraversalMetrics


class TraversalPath(BaseModel):
    """Immutable sequence of nodes and connecting edges forming a path in the graph."""

    model_config = ConfigDict(frozen=True)

    nodes: List[str] = Field(..., description="Ordered node IDs from root to destination")
    edges: List[Dict[str, Any]] = Field(default_factory=list, description="Ordered connecting edge specifications")
    depth: int = Field(0, description="Path depth / length")
    weight: float = Field(1.0, description="Total path cost or weight")

    @property
    def start_node(self) -> Optional[str]:
        return self.nodes[0] if self.nodes else None

    @property
    def end_node(self) -> Optional[str]:
        return self.nodes[-1] if self.nodes else None


class TraversalResult(BaseModel):
    """Immutable final result produced by executing a graph traversal."""

    model_config = ConfigDict(frozen=True)

    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Completion timestamp")
    visited_nodes: List[str] = Field(default_factory=list, description="Ordered list of all visited unique node IDs")
    visited_edges: List[Dict[str, Any]] = Field(default_factory=list, description="List of all visited edge dicts")
    paths: List[TraversalPath] = Field(default_factory=list, description="All discovered paths")
    depth_map: Dict[str, int] = Field(default_factory=dict, description="Map of node_id -> distance/depth from root")
    root_nodes: List[str] = Field(default_factory=list, description="Root node IDs initiating traversal")
    leaf_nodes: List[str] = Field(default_factory=list, description="Terminal / leaf node IDs reached")
    metrics: TraversalMetrics = Field(default_factory=TraversalMetrics, description="Execution metrics")
    diagnostics_summary: Dict[str, Any] = Field(default_factory=dict, description="Diagnostics summary")
    execution_time_ms: float = Field(0.0, description="Total execution duration in milliseconds")


__all__ = ["TraversalPath", "TraversalResult"]
