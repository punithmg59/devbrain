from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    # Database
    database_url: str
    direct_url: str

    # App
    app_url: str = "https://devbrain-backend-production.up.railway.app"
    frontend_url: str = "https://devbrain-gilt.vercel.app"
    secret_key: str
    environment: str = "Production"

    # GitHub
    github_client_id: str
    github_client_secret: str
    # Optional explicit OAuth callback URL. If unset, derived from app_url.
    # Must EXACTLY match a callback URL registered in the GitHub OAuth App.
    github_callback_url: str | None = None

    @property
    def oauth_redirect_uri(self) -> str:
        if self.github_callback_url:
            return self.github_callback_url
        return f"{self.app_url}/api/auth/github/callback"

    # Encryption
    # Base64-encoded 32-byte encryption key for AES-256-GCM
    # Generate with: python -c 'import secrets; print(secrets.token_urlsafe(32))'
    # IMPORTANT: This is development-only. Production should use AWS KMS, Azure Key Vault, etc.
    encryption_key: str | None = None

    # Groq
    groq_api_key: str

    # Anthropic (for AI recommendations)
    anthropic_api_key: str = ""

    # Redis
    redis_url: str = "redis://localhost:6379"

    # Supabase
    supabase_url: str
    supabase_anon_key: str

    # Sentry (optional)
    sentry_dsn: str | None = None

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=False,
        extra="ignore"  # Allow extra environment variables
    )


@lru_cache()
def get_settings() -> Settings:
    return Settings()
