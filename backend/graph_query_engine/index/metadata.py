"""
Index Metadata Model for Graph Query Engine.
"""

from datetime import datetime, timezone
from pydantic import BaseModel, ConfigDict, Field

from graph_query_engine.constants import ENGINE_VERSION


class IndexMetadata(BaseModel):
    """
    Immutable metadata tracking index provenance, build timing, and storage checksums.
    """
    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    builder_version: str = Field(default=ENGINE_VERSION, description="Index builder version")
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Index build completion timestamp",
    )
    source_graph_version: str = Field(default="1.0.0", description="Source graph version")
    storage_version: str = Field(default="1.0.0", description="Storage schema version")
    checksum_placeholder: str = Field(default="sha256_index_placeholder", description="Integrity checksum string")
    config_ref: str = Field(default="default_config", description="Configuration reference string")


__all__ = ["IndexMetadata"]
