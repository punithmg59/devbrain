from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # Database
    database_url: str
    direct_url: str

    # App
    app_url: str = "http://localhost:8000"
    frontend_url: str = "http://localhost:5173"
    secret_key: str
    environment: str = "development"

    # GitHub
    github_client_id: str
    github_client_secret: str

    # Groq
    groq_api_key: str

    # Redis
    redis_url: str = "redis://localhost:6379"

    # Supabase
    supabase_url: str
    supabase_anon_key: str

    # Sentry (optional)
    sentry_dsn: str | None = None

    class Config:
        env_file = ".env"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    return Settings()
