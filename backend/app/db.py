import logging

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import settings

logger = logging.getLogger(__name__)

assert settings.database_url is not None  # set by Settings validator

_connect_args: dict = {
    "timeout": settings.db_connect_timeout_seconds,
    "command_timeout": settings.db_command_timeout_seconds,
}

engine = create_async_engine(
    settings.database_url,
    echo=False,
    pool_pre_ping=True,
    connect_args=_connect_args,
)

async_session_maker = async_sessionmaker(
    engine,
    expire_on_commit=False,
    class_=AsyncSession,
)


async def check_db_connection() -> bool:
    """Return True if PostgreSQL answers a trivial query."""
    try:
        async with async_session_maker() as session:
            await session.execute(text("SELECT 1 AS one"))
        return True
    except Exception as exc:
        logger.warning(
            "Database health check failed (target=%s): %s",
            settings.log_safe_database_target(),
            exc,
        )
        return False


async def verify_db_on_startup() -> None:
    """Run SELECT 1; raises if the database is unreachable (fail-fast startup)."""
    async with async_session_maker() as session:
        await session.execute(text("SELECT 1 AS one"))
