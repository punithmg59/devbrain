"""
Index Descriptor Model for Graph Query Engine.
"""

from typing import Mapping
from pydantic import BaseModel, ConfigDict, Field


class IndexDescriptor(BaseModel):
    """
    Immutable descriptor defining index metadata, capabilities, and version requirements.
    """
    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    name: str = Field(..., description="Unique index name")
    description: str = Field(default="", description="Human readable description")
    version: str = Field(default="1.0.0", description="Semver index version")
    supported_graph_version: str = Field(default="1.0.0", description="Supported semver graph model version")
    supported_schema_version: str = Field(default="1.0.0", description="Supported semver storage schema version")
    index_type: str = Field(default="GENERAL", description="Index classification type")
    build_strategy: str = Field(default="EAGER", description="Build strategy (EAGER, LAZY, ON_DEMAND)")
    dependencies: tuple[str, ...] = Field(default_factory=tuple, description="Prerequisite index dependencies")
    capabilities: Mapping[str, bool] = Field(default_factory=dict, description="Capabilities supported by index")


__all__ = ["IndexDescriptor"]
