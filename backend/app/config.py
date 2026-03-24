from __future__ import annotations

from typing import Literal, Self
from urllib.parse import quote_plus, urlparse

from pydantic import AliasChoices, Field, model_validator
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

    mistral_api_key: str | None = Field(default=None, validation_alias="MISTRAL_API_KEY")
    video_storage_root: str = Field(default="/data/videos", validation_alias="VIDEO_STORAGE_ROOT")
    video_upload_max_bytes: int = Field(
        default=500 * 1024 * 1024,
        validation_alias="VIDEO_UPLOAD_MAX_BYTES",
    )
    mistral_transcription_model: str = Field(
        default="voxtral-mini-latest",
        validation_alias="MISTRAL_TRANSCRIPTION_MODEL",
    )
    mistral_embedding_model: str = Field(
        default="mistral-embed",
        validation_alias="MISTRAL_EMBEDDING_MODEL",
    )
    # Mistral embeddings API rejects a single request with too many inputs (split into batches).
    mistral_embed_batch_size: int = Field(
        default=32,
        ge=1,
        le=512,
        validation_alias="MISTRAL_EMBED_BATCH_SIZE",
    )
    # Macro transcript units: primary mode is word-like target (PRD); chars optional for legacy tuning.
    transcript_macro_target_mode: Literal["words", "chars"] = Field(
        default="words",
        validation_alias="TRANSCRIPT_MACRO_TARGET_MODE",
    )
    transcript_macro_target_words: int = Field(
        default=280,
        ge=10,
        le=5000,
        validation_alias="TRANSCRIPT_MACRO_TARGET_WORDS",
    )
    transcript_macro_target_chars: int = Field(
        default=1600,
        ge=50,
        le=100_000,
        validation_alias="TRANSCRIPT_MACRO_TARGET_CHARS",
    )
    # Phase-1 macro shortlist: max macros after adaptive filtering (alias keeps older env name working).
    search_macro_top_k_max: int = Field(
        default=5,
        ge=1,
        le=50,
        validation_alias=AliasChoices("SEARCH_MACRO_TOP_K_MAX", "SEARCH_COARSE_TOP_N"),
    )
    # Hybrid retrieval context size sent to extractor (post-fusion top-K).
    search_macro_top_k: int = Field(
        default=10,
        ge=1,
        le=50,
        validation_alias="SEARCH_MACRO_TOP_K",
    )
    # Reciprocal Rank Fusion constant (default from architecture/story).
    search_rrf_k: int = Field(
        default=60,
        ge=1,
        le=500,
        validation_alias="SEARCH_RRF_K",
    )
    # Cosine distance in [0, 2]: drop macros farther than this from the query embedding.
    search_macro_max_cosine_distance: float = Field(
        default=0.95,
        ge=0.0,
        le=2.0,
        validation_alias="SEARCH_MACRO_MAX_COSINE_DISTANCE",
    )
    # Exclude macros whose distance exceeds best macro distance by more than this (adaptive K).
    search_macro_gap_from_best: float = Field(
        default=0.18,
        ge=0.0,
        le=2.0,
        validation_alias="SEARCH_MACRO_GAP_FROM_BEST",
    )
    mistral_anchor_model: str = Field(
        default="mistral-small-latest",
        validation_alias="MISTRAL_ANCHOR_MODEL",
    )
    mistral_anchor_max_tokens: int = Field(
        default=1024,
        ge=64,
        le=8192,
        validation_alias="MISTRAL_ANCHOR_MAX_TOKENS",
    )

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


def sync_database_url_for_alembic(database_url: str | None) -> str:
    """Convert async SQLAlchemy URL to sync psycopg (v3) URL for Alembic migrations."""
    if not database_url:
        raise ValueError("database_url is required for migrations")
    url = database_url.strip()
    if url.startswith("postgresql+asyncpg://"):
        return url.replace("postgresql+asyncpg://", "postgresql+psycopg://", 1)
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+psycopg://", 1)
    raise ValueError(
        "Unsupported database URL for Alembic (expected postgresql+asyncpg:// or postgresql://)"
    )


settings = Settings()
