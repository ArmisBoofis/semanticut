"""
Test env: skip real DB startup; use a dummy DATABASE_URL so Settings / engine load.
"""

import os

# Must run before any `app.*` import (Settings loads at import time).
os.environ["DATABASE_URL"] = "postgresql+asyncpg://test:test@127.0.0.1:5432/test"
os.environ["SKIP_DB_STARTUP"] = "1"

import subprocess
import sys
from pathlib import Path

import httpx
import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import sync_database_url_for_alembic

_BACKEND_ROOT = Path(__file__).resolve().parent.parent


def _reset_public_schema_for_tests(sync_url: str) -> None:
    """Drop and recreate public schema so `alembic upgrade head` matches a clean database."""
    engine = create_engine(sync_url)
    with engine.begin() as conn:
        conn.execute(text("DROP SCHEMA IF EXISTS public CASCADE"))
        conn.execute(text("CREATE SCHEMA public"))
        conn.execute(text("GRANT ALL ON SCHEMA public TO public"))
    engine.dispose()


def _run_alembic_upgrade_head(async_database_url: str) -> None:
    """Apply Alembic migrations in a subprocess (fresh Settings + same env as production)."""
    env = {**os.environ, "DATABASE_URL": async_database_url}
    subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=str(_BACKEND_ROOT),
        env=env,
        check=True,
    )


@pytest.fixture
async def video_engine():
    """PostgreSQL async URL; integration tests skip if unset."""
    url = os.environ.get("TEST_DATABASE_URL")
    if not url:
        pytest.skip(
            "Set TEST_DATABASE_URL to a PostgreSQL async URL (postgresql+asyncpg://...) "
            "to run video API integration tests"
        )

    sync_url = sync_database_url_for_alembic(url)
    _reset_public_schema_for_tests(sync_url)
    _run_alembic_upgrade_head(url)

    engine = create_async_engine(url)
    yield engine
    await engine.dispose()


@pytest.fixture
async def video_client(video_engine):
    from app.deps import get_db_session
    from app.main import app

    async_session = async_sessionmaker(
        video_engine,
        expire_on_commit=False,
        class_=AsyncSession,
    )

    async def override_get_db():
        async with async_session() as session:
            yield session

    app.dependency_overrides[get_db_session] = override_get_db
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
    app.dependency_overrides.clear()
