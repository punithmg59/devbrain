"""
Public Query API Result, Statistics, and Diagnostics Models.

Encapsulates engineering-friendly query outputs, execution timing statistics, and diagnostic traces.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class QueryStatistics(BaseModel):
    """Immutable execution metrics and timing statistics model."""

    model_config = ConfigDict(frozen=True)

    planning_time_ms: float = Field(default=0.0, ge=0.0, description="Planning phase duration in milliseconds")
    optimization_time_ms: float = Field(default=0.0, ge=0.0, description="Plan optimization phase duration in milliseconds")
    execution_time_ms: float = Field(default=0.0, ge=0.0, description="Graph traversal execution duration in milliseconds")
    total_duration_ms: float = Field(default=0.0, ge=0.0, description="Total request handling duration in milliseconds")
    nodes_visited: int = Field(default=0, ge=0, description="Total graph nodes visited")
    edges_visited: int = Field(default=0, ge=0, description="Total graph edges visited")
    paths_explored: int = Field(default=0, ge=0, description="Total paths explored")
    result_count: int = Field(default=0, ge=0, description="Total items returned in QueryResult")


class QueryDiagnostics(BaseModel):
    """Immutable diagnostic information summary for Public Query API responses."""

    model_config = ConfigDict(frozen=True)

    query_summary: str = Field(default="", description="High-level engineering query execution summary")
    planner_statistics: Dict[str, Any] = Field(default_factory=dict, description="Logical/Physical/Execution planner details")
    execution_statistics: Dict[str, Any] = Field(default_factory=dict, description="Traversal pipeline execution details")
    traversal_statistics: Dict[str, Any] = Field(default_factory=dict, description="Graph traversal metrics summary")
    warnings: List[str] = Field(default_factory=list, description="List of non-fatal execution warnings")
    errors: List[str] = Field(default_factory=list, description="List of execution errors encountered")


class QueryResult(BaseModel):
    """
    Immutable engineering-centric query result model.
    Hides internal graph algorithm details and presents clean engineering objects.
    """

    model_config = ConfigDict(frozen=True)

    target: str = Field(default="", description="Target symbol, path, or entity of the query")
    nodes: List[Dict[str, Any]] = Field(default_factory=list, description="List of matching engineering nodes or symbols")
    edges: List[Dict[str, Any]] = Field(default_factory=list, description="List of connecting relationships or call edges")
    paths: List[List[str]] = Field(default_factory=list, description="Discovered paths represented as node ID sequences")
    records: List[Dict[str, Any]] = Field(default_factory=list, description="Structured tabular rows or key-value properties")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Operation-specific output metadata")

    @property
    def is_empty(self) -> bool:
        """Returns True if no nodes, paths, or records were returned."""
        return not bool(self.nodes or self.paths or self.records)


__all__ = ["QueryStatistics", "QueryDiagnostics", "QueryResult"]
