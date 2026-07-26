"""
IndexSnapshot Model for Describing Immutable Index State.
"""

from datetime import datetime, timezone
from typing import Mapping
from pydantic import BaseModel, ConfigDict, Field

from graph_query_engine.view.identity import GraphIdentity


class IndexSnapshot(BaseModel):
    """
    Immutable representation of an active set of indexes over a GraphView snapshot.
    """
    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    snapshot_id: str = Field(..., description="Unique index snapshot identifier")
    graph_identity: GraphIdentity = Field(..., description="Source GraphIdentity reference")
    active_index_names: tuple[str, ...] = Field(default_factory=tuple, description="Names of active indexes")
    graph_version: str = Field(default="1.0.0", description="Semver graph model version")
    schema_version: str = Field(default="1.0.0", description="Semver schema version")
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="UTC timestamp of snapshot creation",
    )


__all__ = ["IndexSnapshot"]
