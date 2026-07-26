"""
Graph Snapshot Information Model for Graph Query Engine.
"""

from datetime import datetime, timezone
from pydantic import BaseModel, ConfigDict, Field

from graph_query_engine.types import SnapshotId


class GraphSnapshotInfo(BaseModel):
    """
    Immutable snapshot provenance and integrity information.
    """
    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    snapshot_id: SnapshotId = Field(..., description="Snapshot identifier")
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Snapshot creation timestamp",
    )
    snapshot_version: str = Field(default="1.0.0", description="Snapshot format version")
    graph_hash: str = Field(default="", description="Cryptographic SHA256 hash of graph contents")
    checksum: str = Field(default="", description="Integrity checksum string")
    graph_size_bytes: int = Field(default=0, ge=0, description="In-memory byte footprint estimate")


__all__ = ["GraphSnapshotInfo"]
