"""
core/dependency_graph/statistics.py
-----------------------------------
Execution metrics and density statistics model for DependencyGraph.
"""

from __future__ import annotations

from typing import Dict
from pydantic import BaseModel, Field


class DependencyGraphStatistics(BaseModel):
    """
    Graph metrics and density statistics for DependencyGraph.
    """
    total_nodes: int = Field(default=0, ge=0, description="Total node count in graph")
    total_edges: int = Field(default=0, ge=0, description="Total edge count in graph")
    edges_by_kind_counts: Dict[str, int] = Field(default_factory=dict, description="Edge count by EdgeKind")
    nodes_by_language_counts: Dict[str, int] = Field(default_factory=dict, description="Node count by Language")
    nodes_by_kind_counts: Dict[str, int] = Field(default_factory=dict, description="Node count by SymbolKind")
    graph_density: float = Field(default=0.0, ge=0.0, description="Ratio of edges to maximum possible directed edges (|E| / (|V|*(|V|-1)))")
    duration_ms: float = Field(default=0.0, ge=0.0, description="Graph assembly duration in milliseconds")

    model_config = {
        "frozen": True
    }
