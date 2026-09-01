"""
Application configuration via Pydantic Settings.

All configuration comes from environment variables / .env file.
No secrets are hardcoded.
"""

from typing import Any

from pydantic import AliasChoices, Field
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
    reviewer_tokens_raw: str | None = Field(
        default=None,
        validation_alias=AliasChoices("REVIEWER_TOKENS", "reviewer_tokens"),
    )
    reviewer_token: str | None = Field(
        default=None,
        validation_alias=AliasChoices("REVIEWER_TOKEN", "reviewer_token"),
    )

    @staticmethod
    def _parse_reviewer_tokens(*token_sources: str | None) -> list[str]:
        tokens: list[str] = []
        for token_source in token_sources:
            if not token_source:
                continue
            for token in token_source.split(","):
                cleaned = token.strip()
                if cleaned:
                    tokens.append(cleaned)

        unique_tokens: list[str] = []
        seen: set[str] = set()
        for token in tokens:
            if token not in seen:
                seen.add(token)
                unique_tokens.append(token)
        return unique_tokens

    @property
    def reviewer_tokens(self) -> list[str]:
        return self._parse_reviewer_tokens(self.reviewer_tokens_raw, self.reviewer_token)

    # --- CORS ---
    # Comma-separated string in env; parsed into a list.
    cors_allowed_origins: list[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
    ]


settings = Settings()
