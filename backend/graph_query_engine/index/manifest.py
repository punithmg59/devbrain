"""
IndexManifest Model for Index Registration and Dependency Tracking.
"""

from datetime import datetime, timezone
from typing import Mapping
from pydantic import BaseModel, ConfigDict, Field


class IndexManifest(BaseModel):
    """
    Immutable manifest detailing registered index descriptors, dependencies, and semver bounds.
    """
    model_config = ConfigDict(frozen=True)

    manifest_version: str = Field(default="1.0.0", description="Semver manifest schema version")
    registered_index_types: tuple[str, ...] = Field(default_factory=tuple, description="Registered index class names")
    index_dependencies: Mapping[str, tuple[str, ...]] = Field(
        default_factory=dict,
        description="Mapping of index_name -> tuple of dependency index names",
    )
    supported_graph_version: str = Field(default="1.0.0", description="Supported semver graph version")
    supported_schema_version: str = Field(default="1.0.0", description="Supported semver schema version")
    generated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="UTC timestamp of manifest generation",
    )


__all__ = ["IndexManifest"]
