"""
GraphIdentity Value Object for Graph Query Engine.

Encapsulates immutable graph identity attributes (RepositoryId, SnapshotId, versions, hash).
"""

from pydantic import BaseModel, ConfigDict, Field

from graph_query_engine.constants import ENGINE_VERSION
from graph_query_engine.types import LanguageId, RepositoryId, SnapshotId


class GraphIdentity(BaseModel):
    """
    Immutable representation of a graph snapshot identity.
    """
    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    repository_id: RepositoryId = Field(..., description="Repository identifier")
    snapshot_id: SnapshotId = Field(..., description="Snapshot identifier")
    graph_version: str = Field(default="1.0.0", description="Semver graph model version")
    schema_version: str = Field(default="1.0.0", description="Semver schema version")
    analyzer_version: str = Field(default=ENGINE_VERSION, description="Analyzer software version")
    graph_hash: str = Field(default="", description="SHA256 hash of graph contents")
    language: LanguageId = Field(default=LanguageId("python"), description="Primary language identifier")


__all__ = ["GraphIdentity"]
