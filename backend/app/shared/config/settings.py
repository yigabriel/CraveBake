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
    access_token_expire_minutes: int = 60

    # Origins allowed to call the API from a browser. In `.env` it is set as a
    # JSON list, e.g. CORS_ALLOWED_ORIGINS=["https://cravebake.app"]
    cors_allowed_origins: list[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://localhost:4200",
    ]

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


@lru_cache
def get_settings() -> Settings:
    """Returns a cached Settings instance (loaded once per process)."""
    return Settings()
