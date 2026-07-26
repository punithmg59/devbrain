"""
Graph Metadata Model for Graph Query Engine.
"""

from datetime import datetime, timezone
from pydantic import BaseModel, ConfigDict, Field

from graph_query_engine.types import LanguageId, RepositoryId, SnapshotId
from graph_query_engine.view.identity import GraphIdentity


class GraphMetadata(BaseModel):
    """
    Immutable metadata associated with a GraphView instance.

    References GraphIdentity for core snapshot identification.
    """
    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    identity: GraphIdentity = Field(..., description="Immutable GraphIdentity reference")
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Graph snapshot creation timestamp",
    )
    repository_name: str = Field(default="", description="Repository display name")
    branch: str = Field(default="main", description="Git branch name")
    commit_sha: str = Field(default="HEAD", description="Git commit hash")
    statistics_ref: str = Field(default="", description="Reference hash/key to graph statistics")

    @property
    def repository_id(self) -> RepositoryId:
        """Delegates to identity.repository_id."""
        return self.identity.repository_id

    @property
    def snapshot_id(self) -> SnapshotId:
        """Delegates to identity.snapshot_id."""
        return self.identity.snapshot_id

    @property
    def graph_version(self) -> str:
        """Delegates to identity.graph_version."""
        return self.identity.graph_version

    @property
    def schema_version(self) -> str:
        """Delegates to identity.schema_version."""
        return self.identity.schema_version

    @property
    def analyzer_version(self) -> str:
        """Delegates to identity.analyzer_version."""
        return self.identity.analyzer_version

    @property
    def language(self) -> LanguageId:
        """Delegates to identity.language."""
        return self.identity.language


__all__ = ["GraphMetadata"]
