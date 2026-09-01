"""
Application configuration via Pydantic Settings.

All configuration comes from environment variables / .env file.
No secrets are hardcoded.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # --- Application ---
    app_env: str = "development"
    app_debug: bool = False

    # --- Database ---
    database_url: str = "postgresql://sih_user:changeme@localhost:5432/sih_dev"

    # --- API ---
    api_v1_prefix: str = "/api/v1"

    # --- Security ---
    reviewer_token: str

    # --- CORS ---
    # Comma-separated string in env; parsed into a list.
    cors_allowed_origins: list[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
    ]


settings = Settings()
