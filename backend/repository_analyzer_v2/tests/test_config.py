import os
import pytest
from pydantic import ValidationError

from config.settings import (
    AnalyzerSettings,
    EnvironmentType,
    LogLevel,
    get_settings,
)

def test_default_settings(monkeypatch):
    """Test loading settings with minimum required values."""
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@localhost:5432/db")
    monkeypatch.setenv("DEBUG_MODE", "false")
    
    # Clear lru_cache for testing
    get_settings.cache_clear()
    settings = get_settings()
    
    assert settings.database_url == "postgresql://user:pass@localhost:5432/db"
    assert settings.environment == EnvironmentType.DEVELOPMENT
    assert settings.debug_mode is False
    assert settings.worker_count == 4
    assert settings.max_memory_mb == 1024
    assert settings.max_file_size_kb == 5000
    assert settings.file_timeout_seconds == 30
    assert "python" in settings.supported_languages
    assert settings.log_level == LogLevel.INFO
    assert settings.metrics_enabled is True
    assert settings.cache.enabled is True

def test_custom_settings(monkeypatch):
    """Test overriding settings via environment variables."""
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://user:pass@localhost/prod")
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("DEBUG_MODE", "true")
    monkeypatch.setenv("WORKER_COUNT", "16")
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")
    monkeypatch.setenv("SUPPORTED_LANGUAGES", '["python", "go", "rust"]')
    monkeypatch.setenv("CACHE__ENABLED", "false")
    
    get_settings.cache_clear()
    settings = get_settings()
    
    assert settings.environment == EnvironmentType.PRODUCTION
    assert settings.debug_mode is True
    assert settings.worker_count == 16
    assert settings.log_level == LogLevel.DEBUG
    assert settings.supported_languages == ["python", "go", "rust"]
    assert settings.cache.enabled is False

def test_invalid_database_url(monkeypatch):
    """Test validation failure for invalid database URL."""
    monkeypatch.setenv("DATABASE_URL", "mysql://user:pass@localhost/db")
    get_settings.cache_clear()
    
    with pytest.raises(ValidationError) as exc:
        get_settings()
    
    assert "Database URL must be a valid PostgreSQL connection string" in str(exc.value)

def test_invalid_worker_count(monkeypatch):
    """Test validation failure for out of bounds worker count."""
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@localhost/db")
    monkeypatch.setenv("WORKER_COUNT", "200") # Max is 128
    get_settings.cache_clear()
    
    with pytest.raises(ValidationError):
        get_settings()

def test_cache_singleton(monkeypatch):
    """Test that get_settings() returns the same cached instance."""
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@localhost:5432/db")
    get_settings.cache_clear()
    
    instance1 = get_settings()
    instance2 = get_settings()
    
    assert instance1 is instance2
