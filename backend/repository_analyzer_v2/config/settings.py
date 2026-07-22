from enum import Enum
from functools import lru_cache
from typing import List, Literal, Optional
from pydantic import BaseModel, Field, field_validator, PostgresDsn
from pydantic_settings import BaseSettings, SettingsConfigDict


class EnvironmentType(str, Enum):
    DEVELOPMENT = "development"
    TESTING = "testing"
    PRODUCTION = "production"


class LogLevel(str, Enum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class CacheConfig(BaseModel):
    """Configuration for caching subsystem."""
    enabled: bool = True
    ttl_seconds: int = 3600
    redis_url: Optional[str] = None


class AnalyzerSettings(BaseSettings):
    """
    Core configuration for the DevBrain Repository Analyzer.
    Loads settings from environment variables and .env file.
    """
    # Environment
    environment: EnvironmentType = Field(default=EnvironmentType.DEVELOPMENT, alias="ENVIRONMENT")
    debug_mode: bool = Field(default=False, alias="DEBUG_MODE")

    # Database
    database_url: str = Field(
        default="postgresql+asyncpg://postgres:postgres@localhost:5432/devbrain",
        alias="DATABASE_URL",
        description="PostgreSQL database URL",
    )

    # Worker & Performance
    worker_count: int = Field(default=4, ge=1, le=128, alias="WORKER_COUNT")
    max_memory_mb: int = Field(default=1024, ge=128, alias="MAX_MEMORY_MB", description="Max memory in MB per worker")
    
    # File Processing Limits
    max_file_size_kb: int = Field(default=5000, ge=1, alias="MAX_FILE_SIZE_KB", description="Max file size in KB")
    file_timeout_seconds: int = Field(default=30, ge=1, alias="FILE_TIMEOUT_SECONDS")
    
    # Supported Languages
    supported_languages: List[str] = Field(
        default_factory=lambda: ["python", "typescript", "javascript", "java", "go", "csharp"],
        alias="SUPPORTED_LANGUAGES"
    )

    # Observability
    log_level: LogLevel = Field(default=LogLevel.INFO, alias="LOG_LEVEL")
    metrics_enabled: bool = Field(default=True, alias="METRICS_ENABLED")

    # Nested configurations
    cache: CacheConfig = Field(default_factory=CacheConfig)
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_nested_delimiter="__",
        extra="ignore"
    )

    @field_validator("database_url")
    @classmethod
    def validate_database_url(cls, v: str) -> str:
        """Ensure database URL is a valid PostgreSQL or SQLite connection string."""
        if not v.startswith(("postgres://", "postgresql://", "postgresql+asyncpg://", "sqlite://", "sqlite+aiosqlite://")):
            raise ValueError("Database URL must be a valid PostgreSQL connection string")
        return v

    @field_validator("supported_languages", mode="before")
    @classmethod
    def parse_languages(cls, v):
        """Parse comma-separated list of languages if passed as a string."""
        if isinstance(v, str):
            return [lang.strip().lower() for lang in v.split(",") if lang.strip()]
        return v


@lru_cache()
def get_settings() -> AnalyzerSettings:
    """
    Returns the cached configuration settings.
    Uses lru_cache to ensure we only read the environment and .env file once.
    """
    return AnalyzerSettings()
