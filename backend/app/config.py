from __future__ import annotations

from typing import Self
from urllib.parse import quote_plus, urlparse

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def build_database_url_from_postgres(
    user: str,
    password: str,
    host: str,
    port: int,
    database: str,
) -> str:
    """Build async SQLAlchemy URL with URL-safe user/password (handles @, :, %, etc.)."""
    u = quote_plus(user)
    p = quote_plus(password)
    return f"postgresql+asyncpg://{u}:{p}@{host}:{port}/{database}"


class Settings(BaseSettings):
    """Application settings from environment (Docker Compose / .env)."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Optional override; if unset, URL is built from POSTGRES_* (safe quoting for passwords).
    database_url: str | None = Field(default=None, validation_alias="DATABASE_URL")
    postgres_user: str | None = Field(default=None, validation_alias="POSTGRES_USER")
    postgres_password: str | None = Field(default=None, validation_alias="POSTGRES_PASSWORD")
    postgres_db: str | None = Field(default=None, validation_alias="POSTGRES_DB")
    postgres_host: str = Field(default="localhost", validation_alias="POSTGRES_HOST")
    postgres_port: int = Field(default=5432, validation_alias="POSTGRES_PORT")

    db_connect_timeout_seconds: float = Field(default=5.0, validation_alias="DB_CONNECT_TIMEOUT")
    db_command_timeout_seconds: float = Field(default=5.0, validation_alias="DB_COMMAND_TIMEOUT")

    @model_validator(mode="after")
    def resolve_database_url(self) -> Self:
        direct = (self.database_url or "").strip() or None
        if direct:
            self.database_url = direct
            return self

        if not self.postgres_user or self.postgres_password is None or not self.postgres_db:
            raise ValueError(
                "Set DATABASE_URL, or POSTGRES_USER, POSTGRES_PASSWORD, and POSTGRES_DB "
                "(e.g. from Docker Compose)."
            )

        self.database_url = build_database_url_from_postgres(
            self.postgres_user,
            self.postgres_password,
            self.postgres_host,
            self.postgres_port,
            self.postgres_db,
        )
        return self

    def log_safe_database_target(self) -> str:
        """Host:port/db for logs — no credentials (parsed from resolved URL)."""
        url = self.database_url
        if not url:
            return "(unknown)"
        parsed = urlparse(url)
        host = parsed.hostname or "(unknown)"
        port = parsed.port or 5432
        name = (parsed.path or "/").lstrip("/") or "(unknown)"
        return f"{host}:{port}/{name}"


settings = Settings()
