"""
Unit tests for Configuration Framework.
"""

import pytest
from pydantic import ValidationError as PydanticValidationError

from graph_query_engine.config import (
    DefaultConfig,
    EnvironmentConfiguration,
    GraphQueryEngineConfig,
)
from graph_query_engine.constants import ENGINE_NAME, ENGINE_VERSION


def test_default_config_creation():
    config = DefaultConfig.create_default()
    assert config.engine_name == ENGINE_NAME
    assert config.engine_version == ENGINE_VERSION
    assert config.max_traversal_depth == 10
    assert config.max_query_results == 1000
    assert config.query_timeout_seconds == 30.0
    assert config.max_memory_mb == 512
    assert config.enable_diagnostics is False


def test_config_immutability():
    config = DefaultConfig.create_default()
    with pytest.raises((TypeError, PydanticValidationError)):
        config.log_level = "DEBUG"  # type: ignore


def test_config_validation_bounds():
    with pytest.raises(PydanticValidationError):
        GraphQueryEngineConfig(max_traversal_depth=0)  # ge=1 constraint

    with pytest.raises(PydanticValidationError):
        GraphQueryEngineConfig(max_memory_mb=10_000)  # le=4096 constraint


def test_environment_configuration_overrides(monkeypatch):
    monkeypatch.setenv("GQE_LOG_LEVEL", "DEBUG")
    monkeypatch.setenv("GQE_MAX_MEMORY_MB", "1024")
    monkeypatch.setenv("GQE_QUERY_TIMEOUT", "60.0")
    monkeypatch.setenv("GQE_ENABLE_DIAGNOSTICS", "true")

    overrides = EnvironmentConfiguration.get_env_overrides()
    assert overrides["log_level"] == "DEBUG"
    assert overrides["max_memory_mb"] == 1024
    assert overrides["query_timeout_seconds"] == 60.0
    assert overrides["enable_diagnostics"] is True
