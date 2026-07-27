# backend/graph_query_engine/traversal/metrics.py
"""Metrics tracking for graph traversals and algorithm execution.
"""

from __future__ import annotations

from typing import Dict
from pydantic import BaseModel, Field, ConfigDict


class TraversalMetrics(BaseModel):
    """Immutable metrics recording execution statistics of a traversal run."""

    model_config = ConfigDict(frozen=True)

    nodes_visited: int = Field(0, description="Total unique nodes visited during traversal")
    edges_visited: int = Field(0, description="Total edges traversed")
    paths_explored: int = Field(0, description="Total paths explored")
    max_depth: int = Field(0, description="Maximum depth reached")
    average_branching_factor: float = Field(0.0, description="Average out-degree of explored nodes")
    execution_duration_ms: float = Field(0.0, description="Execution duration in milliseconds")
    cache_hits: int = Field(0, description="Number of index/adjacency cache hits")
    cache_misses: int = Field(0, description="Number of cache misses")
    algorithm_usage: Dict[str, int] = Field(default_factory=dict, description="Counts of algorithms executed")
    operator_counts: Dict[str, int] = Field(default_factory=dict, description="Counts of operators executed")

    def with_increment(self, **kwargs) -> TraversalMetrics:
        """Return a new TraversalMetrics with updated increments."""
        algo_usage = dict(self.algorithm_usage)
        if "algorithm" in kwargs:
            algo = kwargs["algorithm"]
            algo_usage[algo] = algo_usage.get(algo, 0) + 1

        op_counts = dict(self.operator_counts)
        if "operator" in kwargs:
            op = kwargs["operator"]
            op_counts[op] = op_counts.get(op, 0) + 1

        return TraversalMetrics(
            nodes_visited=self.nodes_visited + kwargs.get("nodes_visited", 0),
            edges_visited=self.edges_visited + kwargs.get("edges_visited", 0),
            paths_explored=self.paths_explored + kwargs.get("paths_explored", 0),
            max_depth=max(self.max_depth, kwargs.get("max_depth", self.max_depth)),
            average_branching_factor=kwargs.get("average_branching_factor", self.average_branching_factor),
            execution_duration_ms=self.execution_duration_ms + kwargs.get("execution_duration_ms", 0.0),
            cache_hits=self.cache_hits + kwargs.get("cache_hits", 0),
            cache_misses=self.cache_misses + kwargs.get("cache_misses", 0),
            algorithm_usage=algo_usage,
            operator_counts=op_counts,
        )


__all__ = ["TraversalMetrics"]
