"""
Statistics Metadata Layer for Cost Model.

Contains metadata metrics only. DOES NOT inspect GraphView or physical graph storage.
"""

from typing import Any, Dict, Optional, Tuple
from pydantic import BaseModel, ConfigDict, Field

from graph_query_engine.types import RepositoryId, SnapshotId


class NodeStatistics(BaseModel):
    """Immutable node population statistics metadata."""
    model_config = ConfigDict(frozen=True)

    total_node_count: int = Field(default=10_000, ge=0, description="Total node count in graph")
    node_type_counts: Dict[str, int] = Field(
        default_factory=lambda: {
            "FUNCTION": 4000,
            "CLASS": 1500,
            "FILE": 1000,
            "MODULE": 500,
            "VARIABLE": 3000,
        },
        description="Node count by node type string",
    )


class EdgeStatistics(BaseModel):
    """Immutable edge population statistics metadata."""
    model_config = ConfigDict(frozen=True)

    total_edge_count: int = Field(default=50_000, ge=0, description="Total edge count in graph")
    average_degree: float = Field(default=5.0, ge=0.0, description="Average node degree")
    min_degree: int = Field(default=0, ge=0, description="Minimum node degree")
    max_degree: int = Field(default=150, ge=0, description="Maximum node degree")
    relationship_type_counts: Dict[str, int] = Field(
        default_factory=lambda: {
            "CALLS": 20000,
            "USES": 15000,
            "INHERITS": 3000,
            "IMPORTS": 7000,
            "CONTAINS": 5000,
        },
        description="Edge count by relationship type string",
    )


class IndexStatisticsMetadata(BaseModel):
    """Immutable index availability and selectivity hints."""
    model_config = ConfigDict(frozen=True)

    available_indexes: Tuple[str, ...] = Field(
        default_factory=lambda: ("PRIMARY_NODE", "QUALIFIED_NAME", "RELATIONSHIP_CSR", "SEMANTIC_SYMBOL"),
        description="Tuple of available index names",
    )
    index_selectivity_hints: Dict[str, float] = Field(
        default_factory=lambda: {
            "PRIMARY_NODE": 0.0001,
            "QUALIFIED_NAME": 0.0001,
            "SEMANTIC_SYMBOL": 0.005,
            "RELATIONSHIP_CSR": 0.05,
        },
        description="Selectivity hints by index name",
    )


class GraphStatisticsMetadata(BaseModel):
    """Immutable graph population statistics metadata payload."""
    model_config = ConfigDict(frozen=True)

    snapshot_id: Optional[SnapshotId] = Field(default=None, description="Graph snapshot ID")
    nodes: NodeStatistics = Field(default_factory=NodeStatistics, description="Node population stats")
    edges: EdgeStatistics = Field(default_factory=EdgeStatistics, description="Edge population stats")
    indexes: IndexStatisticsMetadata = Field(default_factory=IndexStatisticsMetadata, description="Index stats")


class RepositoryStatisticsMetadata(BaseModel):
    """Immutable repository-level statistics wrapper."""
    model_config = ConfigDict(frozen=True)

    repository_id: RepositoryId = Field(..., description="Target RepositoryId")
    graph_stats: GraphStatisticsMetadata = Field(default_factory=GraphStatisticsMetadata, description="Associated graph statistics")


__all__ = [
    "NodeStatistics",
    "EdgeStatistics",
    "IndexStatisticsMetadata",
    "GraphStatisticsMetadata",
    "RepositoryStatisticsMetadata",
]
