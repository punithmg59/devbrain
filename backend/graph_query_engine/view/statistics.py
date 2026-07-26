"""
Graph Statistics Model for Graph Query Engine.
"""

from typing import Mapping
from pydantic import BaseModel, ConfigDict, Field


class GraphStatistics(BaseModel):
    """
    Immutable structural metrics snapshot for a GraphView instance.
    """
    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    node_count: int = Field(default=0, ge=0, description="Total node count")
    edge_count: int = Field(default=0, ge=0, description="Total edge count")
    relationship_counts: Mapping[str, int] = Field(
        default_factory=dict,
        description="Node edge count by RelationshipType key",
    )
    file_count: int = Field(default=0, ge=0, description="Total source files indexed")
    package_count: int = Field(default=0, ge=0, description="Total packages indexed")
    namespace_count: int = Field(default=0, ge=0, description="Total namespaces indexed")
    class_count: int = Field(default=0, ge=0, description="Total class nodes indexed")
    function_count: int = Field(default=0, ge=0, description="Total function nodes indexed")
    api_count: int = Field(default=0, ge=0, description="Total API route nodes indexed")
    max_depth_placeholder: int = Field(default=0, ge=0, description="Placeholder max traversal depth")


__all__ = ["GraphStatistics"]
