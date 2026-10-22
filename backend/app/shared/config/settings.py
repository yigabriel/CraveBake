"""
Application configuration.

Centralizes all environment-driven configuration in a single place so that
no module needs to read `os.environ` directly. This keeps Infrastructure
concerns (secrets, connection strings) out of Domain and Application code.
"""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Crave Bake API"
    debug: bool = False

    database_url: str

    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 3720

    # Failed logins allowed per (client IP, email) before that pair is locked out.
    login_max_failed_attempts: int = 5
    login_lockout_window_seconds: int = 900

    # Origins allowed to call the API from a browser. In `.env` it is set as a
    # JSON list, e.g. CORS_ALLOWED_ORIGINS=["https://cravebake.app"]
    cors_allowed_origins: list[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://localhost:4200",
    ]

    # Photo uploads (Supabase Storage). The secret key stays on the server: browsers
    # only ever get single-use signed URLs. Unset = uploads answer 503.
    supabase_url: str | None = None
    supabase_service_key: str | None = None
    supabase_storage_bucket: str = "recipe-photos"

    # Suggested translations of new catalog names (Google Cloud Translation, Basic v2).
    # The key stays on the server. Unset = suggestions answer 503 and users type the translation.
    google_translate_api_key: str | None = None
    # Each suggestion is billable per character: requests allowed per user in the window.
    translation_max_requests: int = 20
    translation_window_seconds: int = 60

    # Recipe import from a TikTok / Instagram Reel link. Keys stay on the server; unset = the
    # feature answers 503. Every import costs provider credits, hence the per-user limit.
    supadata_api_key: str | None = None
    # The free plan allows 1 request per second; each import makes 2 calls, spaced this far apart.
    supadata_min_interval_seconds: float = 1.1
    gemini_api_key: str | None = None
    gemini_model: str = "gemini-3.5-flash-lite"
    import_max_requests: int = 5
    import_window_seconds: int = 600

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


@lru_cache
def get_settings() -> Settings:
    """Returns a cached Settings instance (loaded once per process)."""
    return Settings()
