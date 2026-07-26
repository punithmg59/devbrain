"""
Immutable Read-Only Node View Model for Graph Query Engine.
"""

from typing import Any, Mapping
from pydantic import BaseModel, ConfigDict, Field

from graph_query_engine.types import (
    FileId,
    LanguageId,
    NamespaceId,
    NodeId,
    PackageId,
)


class ImmutableNodeView(BaseModel):
    """
    Immutable, thread-safe, read-only representation of a graph node.
    """
    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    node_id: NodeId = Field(..., description="Unique node identifier")
    name: str = Field(..., description="Simple node name")
    qualified_name: str = Field(..., description="Fully qualified symbol name")
    node_type: str = Field(..., description="Classification type of node (e.g. FUNCTION, CLASS, MODULE)")
    language: LanguageId | str = Field(default="python", description="Programming language identifier")
    namespace: NamespaceId | str = Field(default="", description="Namespace identifier")
    package: PackageId | str = Field(default="", description="Package identifier")
    file: FileId | str = Field(default="", description="File path identifier")
    attributes: Mapping[str, Any] = Field(default_factory=dict, description="Read-only key-value attribute map")
    relationships: tuple[str, ...] = Field(default_factory=tuple, description="Immutable tuple of relationship keys")
    metadata: Mapping[str, Any] = Field(default_factory=dict, description="Read-only node metadata")


__all__ = ["ImmutableNodeView"]
