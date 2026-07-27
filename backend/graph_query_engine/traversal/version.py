# backend/graph_query_engine/traversal/version.py
"""Version models for the Traversal Engine subsystem.
All models are frozen Pydantic models.
"""

from __future__ import annotations

from pydantic import BaseModel, Field, ConfigDict


class TraversalEngineVersion(BaseModel):
    """Immutable version metadata for the Traversal Engine."""

    model_config = ConfigDict(frozen=True)

    engine_version: str = Field("1.0.0", description="Traversal engine semantic version")
    operator_version: str = Field("1.0.0", description="Operator specification version")
    algorithm_version: str = Field("1.0.0", description="Graph algorithm suite version")
    result_schema_version: str = Field("1.0.0", description="TraversalResult schema version")


__all__ = ["TraversalEngineVersion"]
