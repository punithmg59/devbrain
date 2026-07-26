"""
Index Statistics Model for Graph Query Engine.
"""

from pydantic import BaseModel, ConfigDict, Field


class IndexStatistics(BaseModel):
    """
    Immutable structural and memory metrics model for an index.
    """
    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    memory_estimate_bytes: int = Field(default=0, ge=0, description="Estimated RAM footprint in bytes")
    node_count: int = Field(default=0, ge=0, description="Total node count indexed")
    edge_count: int = Field(default=0, ge=0, description="Total edge count indexed")
    lookup_count_placeholder: int = Field(default=0, ge=0, description="Placeholder total lookup counter")
    build_duration_seconds_placeholder: float = Field(default=0.0, ge=0.0, description="Placeholder build duration")
    storage_size_bytes_placeholder: int = Field(default=0, ge=0, description="Placeholder disk storage footprint")


__all__ = ["IndexStatistics"]
