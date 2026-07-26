"""
Configuration Validator Protocol for Graph Query Engine.
"""

from typing import Protocol

from graph_query_engine.config.config import GraphQueryEngineConfig


class ConfigurationValidator(Protocol):
    """
    Contract for validating configuration constraints before engine startup.
    """

    def validate(self, config: GraphQueryEngineConfig) -> None:
        """
        Validates the given configuration. Raises ConfigurationError if invalid.
        """
        ...
