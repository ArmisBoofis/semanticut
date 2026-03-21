import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from app.config import settings
from app.db import check_db_connection, engine, verify_db_on_startup

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    if os.getenv("SKIP_DB_STARTUP") != "1":
        try:
            await verify_db_on_startup()
        except Exception:
            logger.exception(
                "Database connection failed during startup (target=%s). "
                "Ensure PostgreSQL is reachable and the `db` service is healthy before `api` starts.",
                settings.log_safe_database_target(),
            )
            raise
    yield
    if os.getenv("SKIP_DB_STARTUP") != "1":
        await engine.dispose()


app = FastAPI(
    title="semanticut API",
    lifespan=lifespan,
)


@app.get("/health")
async def health():
    ok = await check_db_connection()
    if not ok:
        return JSONResponse(
            status_code=503,
            content={"status": "unavailable", "database": "error"},
        )
    return {"status": "ok", "database": "ok"}
