import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.config import settings
from app.db import check_db_connection, engine, verify_db_on_startup
from app.errors import AppError
from app.routers import videos

logger = logging.getLogger(__name__)


def _first_validation_message(exc: RequestValidationError) -> str:
    errors = exc.errors()
    if not errors:
        return "validation error"
    first = errors[0]
    loc = ".".join(str(x) for x in first.get("loc", ()) if x not in ("body", "query", "path"))
    msg = first.get("msg", "validation error")
    if loc:
        return f"{loc}: {msg}"
    return msg


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


@app.exception_handler(AppError)
async def app_error_handler(_request, exc: AppError):
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": {"code": exc.code, "message": exc.message}},
    )


@app.exception_handler(RequestValidationError)
async def request_validation_handler(_request, exc: RequestValidationError):
    return JSONResponse(
        status_code=400,
        content={
            "error": {
                "code": "VALIDATION_ERROR",
                "message": _first_validation_message(exc),
            }
        },
    )


app.include_router(videos.router)


@app.get("/health")
async def health():
    ok = await check_db_connection()
    if not ok:
        return JSONResponse(
            status_code=503,
            content={"status": "unavailable", "database": "error"},
        )
    return {"status": "ok", "database": "ok"}
