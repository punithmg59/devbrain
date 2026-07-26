"""
IndexMemoryReport Model for Estimating Index RAM Footprints.
"""

from datetime import datetime, timezone
from pydantic import BaseModel, ConfigDict, Field


class IndexMemoryReport(BaseModel):
    """
    Immutable memory breakdown report estimating RAM footprint across index layers.
    """
    model_config = ConfigDict(frozen=True)

    lookup_index_bytes: int = Field(default=0, ge=0, description="Estimated RAM footprint for core lookup indexes")
    relationship_index_bytes: int = Field(default=0, ge=0, description="Estimated RAM footprint for relationship & CSR indexes")
    semantic_index_bytes: int = Field(default=0, ge=0, description="Estimated RAM footprint for semantic indexes")
    registry_overhead_bytes: int = Field(default=0, ge=0, description="Registry overhead memory footprint")
    total_memory_bytes: int = Field(default=0, ge=0, description="Total estimated index subsystem RAM footprint")
    object_counts: int = Field(default=0, ge=0, description="Total indexed object instances count")
    generated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="UTC timestamp of memory report generation",
    )


__all__ = ["IndexMemoryReport"]
