"""
Immutable Read-Only Edge View Model for Graph Query Engine.
"""

from typing import Any, Mapping
from pydantic import BaseModel, ConfigDict, Field

from graph_query_engine.types import EdgeId, NodeId, RelationshipType


class ImmutableEdgeView(BaseModel):
    """
    Immutable, thread-safe, read-only representation of a graph relationship edge.
    """
    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    edge_id: EdgeId = Field(..., description="Unique edge identifier")
    source_node_id: NodeId = Field(..., description="Source node identifier")
    target_node_id: NodeId = Field(..., description="Target node identifier")
    relationship_type: RelationshipType = Field(..., description="Strongly-typed relationship classification")
    properties: Mapping[str, Any] = Field(default_factory=dict, description="Read-only edge properties")
    metadata: Mapping[str, Any] = Field(default_factory=dict, description="Read-only edge metadata")


__all__ = ["ImmutableEdgeView"]
