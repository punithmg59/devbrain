import logging
import sys
import traceback
import uuid

import sentry_sdk
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sqlalchemy.exc import ProgrammingError, SQLAlchemyError

from app.config import get_settings
from app.database import init_db, test_connection, validate_schema
from app.utils.errors import DevBrainException
from app.utils.redis_client import close_redis, init_redis

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ── Guarded router imports ──────────────────────────────────────────────────
# Any ImportError here means a symbol or module is missing. We log the exact
# module, missing symbol, and the expected location before exiting cleanly so
# the developer can diagnose the issue from the log alone.
try:
    from app.routers import (
        analysis,
        architecture,
        auth,
        change_intelligence,
        flows,
        impact,
        nlq,
        repo_detail,
        repos,
        workflows,
        intelligence,
    )
except (ImportError, ModuleNotFoundError) as _import_exc:
    _tb = traceback.format_exc()
    _symbol = str(_import_exc)
    # Extract missing name from "cannot import name 'Foo' from 'bar'"
    _parts = _symbol.split("'")
    _missing = _parts[1] if len(_parts) >= 2 else _symbol
    _module = getattr(_import_exc, "name", "unknown")
    logger.critical(
        "\n"
        "═══════════════════════════════════════════════════════════\n"
        " STARTUP FAILED — ImportError in router/service layer\n"
        "═══════════════════════════════════════════════════════════\n"
        f" Module    : {_module}\n"
        f" Symbol    : {_missing}\n"
        f" Expected  : app.services.<module> or app.utils.<module>\n"
        f" Full error: {_symbol}\n"
        "───────────────────────────────────────────────────────────\n"
        f"{_tb}"
        "═══════════════════════════════════════════════════════════"
    )
    sys.exit(1)

settings = get_settings()

if settings.sentry_dsn:
    sentry_sdk.init(
        dsn=settings.sentry_dsn,
        integrations=[FastApiIntegration()],
        environment=settings.environment,
    )

app = FastAPI(title="DevBrain API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="", tags=["auth"])
app.include_router(repos.router, prefix="", tags=["repos"])
app.include_router(analysis.router, prefix="", tags=["analysis"])
app.include_router(repo_detail.router, prefix="", tags=["repo-detail"])
app.include_router(impact.router, prefix="", tags=["impact"])
app.include_router(workflows.router, prefix="", tags=["workflows"])
app.include_router(architecture.router, prefix="", tags=["architecture"])
app.include_router(intelligence.router, prefix="", tags=["intelligence"])
app.include_router(flows.router, prefix="", tags=["flows"])
app.include_router(change_intelligence.router, prefix="", tags=["change-intelligence"])
app.include_router(nlq.router, prefix="", tags=["nlq"])


# ── Exception handlers ─────────────────────────────────────────


@app.exception_handler(DevBrainException)
async def devbrain_exception_handler(request: Request, exc: DevBrainException) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.message, "code": exc.code},
    )


@app.exception_handler(ProgrammingError)
async def sqlalchemy_schema_error_handler(request: Request, exc: ProgrammingError) -> JSONResponse:
    """Catch SQLAlchemy ProgrammingError (e.g. missing column) and return a clean
    JSON error instead of crashing with a raw 500 traceback."""
    error_msg = str(exc.orig) if exc.orig else str(exc)
    logger.error("Database schema error on %s %s: %s", request.method, request.url.path, error_msg)

    if "does not exist" in error_msg:
        return JSONResponse(
            status_code=503,
            content={
                "error": "Database schema is out of sync. The server is attempting auto-repair. Please retry in a few seconds.",
                "code": "SCHEMA_MISMATCH",
                "detail": error_msg,
            },
        )

    return JSONResponse(
        status_code=500,
        content={
            "error": "A database error occurred. Please try again.",
            "code": "DATABASE_ERROR",
            "detail": error_msg,
        },
    )


@app.exception_handler(SQLAlchemyError)
async def sqlalchemy_generic_handler(request: Request, exc: SQLAlchemyError) -> JSONResponse:
    """Handles all other SQLAlchemy errors not caught by ProgrammingError handler."""
    cid = str(uuid.uuid4())
    logger.error(
        "[%s] SQLAlchemyError on %s %s\n%s",
        cid, request.method, request.url.path, traceback.format_exc(),
    )
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "stage": "database",
            "error_type": type(exc).__name__,
            "message": "A database error occurred. Please try again.",
            "correlation_id": cid,
            "recoverable": True,
        },
    )


@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError) -> JSONResponse:
    cid = str(uuid.uuid4())
    logger.error("[%s] ValueError on %s %s: %s", cid, request.method, request.url.path, exc)
    return JSONResponse(
        status_code=422,
        content={
            "success": False,
            "stage": "request_validation",
            "error_type": "ValueError",
            "message": str(exc),
            "correlation_id": cid,
            "recoverable": True,
        },
    )


@app.exception_handler(KeyError)
async def key_error_handler(request: Request, exc: KeyError) -> JSONResponse:
    cid = str(uuid.uuid4())
    logger.error("[%s] KeyError on %s %s: %s\n%s", cid, request.method, request.url.path, exc, traceback.format_exc())
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "stage": "processing",
            "error_type": "KeyError",
            "message": "A required data key was missing. Check backend logs for details.",
            "correlation_id": cid,
            "recoverable": True,
        },
    )


@app.exception_handler(TimeoutError)
async def timeout_error_handler(request: Request, exc: TimeoutError) -> JSONResponse:
    cid = str(uuid.uuid4())
    logger.error("[%s] TimeoutError on %s %s: %s", cid, request.method, request.url.path, exc)
    return JSONResponse(
        status_code=504,
        content={
            "success": False,
            "stage": "processing",
            "error_type": "TimeoutError",
            "message": "The request timed out. Try again or simplify your query.",
            "correlation_id": cid,
            "recoverable": True,
        },
    )


@app.exception_handler(RuntimeError)
async def runtime_error_handler(request: Request, exc: RuntimeError) -> JSONResponse:
    cid = str(uuid.uuid4())
    logger.error("[%s] RuntimeError on %s %s\n%s", cid, request.method, request.url.path, traceback.format_exc())
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "stage": "processing",
            "error_type": "RuntimeError",
            "message": "A runtime error occurred. Contact support if this persists.",
            "correlation_id": cid,
            "recoverable": False,
        },
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Catch-all safety net — no raw traceback ever reaches the client."""
    cid = str(uuid.uuid4())
    logger.error(
        "[%s] Unhandled %s on %s %s\n%s",
        cid, type(exc).__name__, request.method, request.url.path,
        traceback.format_exc(),
    )
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "stage": "unknown",
            "error_type": type(exc).__name__,
            "message": "An unexpected error occurred. Please try again or contact support.",
            "correlation_id": cid,
            "recoverable": False,
        },
    )


# ── Startup / Shutdown ─────────────────────────────────────────


_schema_status: dict[str, list[str]] = {}


@app.on_event("startup")
async def startup_event() -> None:
    global _schema_status

    # 1. Redis
    try:
        await init_redis()
    except Exception as e:
        logger.error("Failed to initialize Redis: %s", e)

    # 2. Database tables (create missing tables)
    try:
        await init_db()
    except Exception as e:
        logger.error("Failed to initialize database tables: %s", e)

    # 3. Schema validation (detect & auto-fix missing columns)
    try:
        _schema_status = await validate_schema()
        if _schema_status:
            logger.warning(
                "Schema auto-fix was applied for: %s",
                ", ".join(f"{t}({','.join(cols)})" for t, cols in _schema_status.items()),
            )
    except Exception as e:
        logger.error("Schema validation failed: %s", e)

    # 4. Connection test
    connected = await test_connection()
    if connected:
        logger.info("Database: connected")
    else:
        logger.warning("Database: connection failed")

    logger.info("DevBrain API started")


@app.on_event("shutdown")
async def shutdown_event() -> None:
    await close_redis()
    logger.info("DevBrain API shutting down")


# ── Health check ───────────────────────────────────────────────


@app.get("/health")
async def health_check():
    connected = await test_connection()
    return {
        "status": "healthy" if connected else "degraded",
        "environment": settings.environment,
        "database": "connected" if connected else "disconnected",
        "schema_fixes_applied": _schema_status if _schema_status else None,
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
