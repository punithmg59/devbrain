"""
Configuration Models for Graph Query Engine.
"""

from typing import Any
from pydantic import BaseModel, ConfigDict, Field

from graph_query_engine.constants import (
    DEFAULT_BATCH_SIZE,
    DEFAULT_CACHE_TTL_SECONDS,
    DEFAULT_MAX_MEMORY_MB,
    DEFAULT_MAX_QUERY_RESULTS,
    DEFAULT_MAX_TRAVERSAL_DEPTH,
    DEFAULT_QUERY_TIMEOUT_SECONDS,
    ENGINE_NAME,
    ENGINE_VERSION,
)


class GraphQueryEngineConfig(BaseModel):
    """
    Immutable, validated configuration model for Graph Query Engine.
    """
    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    engine_name: str = Field(
        default=ENGINE_NAME,
        description="Name of the Graph Query Engine instance.",
    )
    engine_version: str = Field(
        default=ENGINE_VERSION,
        description="Version of the Graph Query Engine binary.",
    )
    log_level: str = Field(
        default="INFO",
        description="Active logging level threshold.",
    )
    max_traversal_depth: int = Field(
        default=DEFAULT_MAX_TRAVERSAL_DEPTH,
        ge=1,
        le=100,
        description="Maximum depth allowed for path and reachability queries.",
    )
    max_query_results: int = Field(
        default=DEFAULT_MAX_QUERY_RESULTS,
        ge=1,
        le=100_000,
        description="Maximum number of node/edge records returned in a single query.",
    )
    query_timeout_seconds: float = Field(
        default=DEFAULT_QUERY_TIMEOUT_SECONDS,
        gt=0.0,
        le=300.0,
        description="Execution budget timeout in seconds.",
    )
    max_memory_mb: int = Field(
        default=DEFAULT_MAX_MEMORY_MB,
        ge=64,
        le=4096,
        description="Maximum RAM allocation limit for query buffers in megabytes.",
    )
    batch_size: int = Field(
        default=DEFAULT_BATCH_SIZE,
        ge=1,
        le=5_000,
        description="Default stream batch size for query result iterators.",
    )
    cache_ttl_seconds: int = Field(
        default=DEFAULT_CACHE_TTL_SECONDS,
        ge=0,
        description="Time-to-live for cached query plans or indices.",
    )
    enable_diagnostics: bool = Field(
        default=False,
        description="Enables diagnostic telemetry and execution metrics collection.",
    )
    custom_settings: dict[str, Any] = Field(
        default_factory=dict,
        description="Extensible dictionary for future component settings.",
    )


class DefaultConfig:
    """
    Factory helper providing canonical default configurations.
    """

    @classmethod
    def create_default(cls) -> GraphQueryEngineConfig:
        """
        Creates a new GraphQueryEngineConfig instance with default values.
        """
        return GraphQueryEngineConfig()
