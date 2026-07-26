"""
Centralized constants for the Graph Query Engine.

Defines engine metadata, limits, defaults, reserved keywords, and configuration keys.
"""

from typing import Final

# Engine Information
ENGINE_NAME: Final[str] = "DevBrain-GraphQueryEngine"
ENGINE_VERSION: Final[str] = "1.0.0-alpha.1"

# Query Default Limits
DEFAULT_MAX_TRAVERSAL_DEPTH: Final[int] = 10
MAX_TRAVERSAL_DEPTH_LIMIT: Final[int] = 100
DEFAULT_MAX_QUERY_RESULTS: Final[int] = 1_000
MAX_QUERY_RESULTS_LIMIT: Final[int] = 100_000

# Execution & Resource Defaults
DEFAULT_QUERY_TIMEOUT_SECONDS: Final[float] = 30.0
MAX_QUERY_TIMEOUT_SECONDS: Final[float] = 300.0
DEFAULT_MAX_MEMORY_MB: Final[int] = 512
MAX_MEMORY_MB_LIMIT: Final[int] = 4096
DEFAULT_BATCH_SIZE: Final[int] = 250
DEFAULT_CACHE_TTL_SECONDS: Final[int] = 300

# Environment Configuration Keys
ENV_CONFIG_PREFIX: Final[str] = "GQE_"
ENV_KEY_LOG_LEVEL: Final[str] = "GQE_LOG_LEVEL"
ENV_KEY_MAX_MEMORY_MB: Final[str] = "GQE_MAX_MEMORY_MB"
ENV_KEY_QUERY_TIMEOUT: Final[str] = "GQE_QUERY_TIMEOUT"
ENV_KEY_ENABLE_DIAGNOSTICS: Final[str] = "GQE_ENABLE_DIAGNOSTICS"

# Reserved Query Keywords
RESERVED_KEYWORDS: Final[tuple[str, ...]] = (
    "MATCH",
    "WHERE",
    "RETURN",
    "TRAVERSE",
    "DEPTH",
    "LIMIT",
    "OFFSET",
    "ORDER_BY",
    "FILTER",
    "SNAPSHOT",
    "WITH",
    "UNION",
)

# Placeholder Constants for Future Execution Steps (Steps 2+)
PLACEHOLDER_PLANNER_STRATEGY: Final[str] = "COST_BASED_DETERMINISTIC"
PLACEHOLDER_STORAGE_READ_MODE: Final[str] = "IMMUTABLE_SNAPSHOT"
