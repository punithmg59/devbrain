"""
Pytest configuration and shared fixtures for Graph Query Engine tests.
"""

import pytest

from graph_query_engine.config import DefaultConfig, GraphQueryEngineConfig


@pytest.fixture
def default_config() -> GraphQueryEngineConfig:
    """Provides a default GraphQueryEngineConfig instance."""
    return DefaultConfig.create_default()
