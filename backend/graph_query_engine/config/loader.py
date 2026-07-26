"""
Configuration Loader Protocol for Graph Query Engine.
"""

from typing import Any, Mapping, Protocol

from graph_query_engine.config.config import GraphQueryEngineConfig


class ConfigurationLoader(Protocol):
    """
    Contract for loading configuration from dictionary, environment, or file sources.
    """

    def load(
        self,
        overrides: Mapping[str, Any] | None = None,
    ) -> GraphQueryEngineConfig:
        """
        Loads and returns a fully validated GraphQueryEngineConfig instance.
        """
        ...
