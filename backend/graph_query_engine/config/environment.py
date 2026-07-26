"""
Environment-based Configuration Loader for Graph Query Engine.
"""

import os
from typing import Any

from graph_query_engine.constants import (
    ENV_KEY_ENABLE_DIAGNOSTICS,
    ENV_KEY_LOG_LEVEL,
    ENV_KEY_MAX_MEMORY_MB,
    ENV_KEY_QUERY_TIMEOUT,
)


class EnvironmentConfiguration:
    """
    Utility for extracting configuration overrides from environment variables.
    """

    @classmethod
    def get_env_overrides(cls) -> dict[str, Any]:
        """
        Reads environment variables with prefix 'GQE_' and returns typed override dictionary.
        """
        overrides: dict[str, Any] = {}

        if log_level := os.getenv(ENV_KEY_LOG_LEVEL):
            overrides["log_level"] = log_level.upper()

        if max_mem := os.getenv(ENV_KEY_MAX_MEMORY_MB):
            try:
                overrides["max_memory_mb"] = int(max_mem)
            except ValueError:
                pass

        if timeout := os.getenv(ENV_KEY_QUERY_TIMEOUT):
            try:
                overrides["query_timeout_seconds"] = float(timeout)
            except ValueError:
                pass

        if diag := os.getenv(ENV_KEY_ENABLE_DIAGNOSTICS):
            overrides["enable_diagnostics"] = diag.lower() in ("true", "1", "yes")

        return overrides
