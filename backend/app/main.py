import asyncio
import logging
import sys

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

import sentry_sdk

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sqlalchemy.exc import ProgrammingError

from app.config import get_settings
from app.database import db_connect_with_backoff, init_db, test_connection, validate_schema
from app.routers import (
    analysis,
    architecture,
    auth,
    flows,
    impact,
    repo_detail,
    repos,
    workflows,
)
from app.services.pipeline.orchestrator import worker_loop as _worker_loop
from app.utils.errors import DevBrainException
from app.utils.oauth_state_storage import OAuthStateStorageFactory, shutdown_oauth_state_storage
from app.utils.redis_client import close_redis, init_redis

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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

app.include_router(flows.router, prefix="", tags=["flows"])


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


# ── Startup / Shutdown ─────────────────────────────────────────


_schema_status: dict[str, list[str]] = {}
_stop_event: asyncio.Event | None = None
_worker_task: asyncio.Task | None = None


@app.on_event("startup")
async def startup_event() -> None:
    global _schema_status, _stop_event, _worker_task

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

    # 4. Database connectivity check with exponential backoff.
    # This replaces a bare test_connection() call so that transient startup
    # failures (e.g. Supabase cold-start, network blip) are retried gracefully
    # instead of causing the worker loop to enter a tight error cycle.
    db_ok = await db_connect_with_backoff(max_attempts=5, base_delay=2.0, max_delay=60.0)
    if db_ok:
        logger.info("Database: connected")
    else:
        logger.warning(
            "Database: connection could not be established after retries. "
            "Worker loop will NOT start. Check DATABASE_URL and Supabase project status."
        )

    # 5. Start worker loop — only if DB is reachable.
    # Avoids a tight error loop (every 1-2 s) when the database is down.
    _stop_event = asyncio.Event()
    if db_ok:
        _worker_task = asyncio.create_task(_worker_loop(_stop_event))
        logger.info("DevBrain worker loop started")
    else:
        logger.error(
            "DevBrain worker loop NOT started (database unreachable). "
            "Redeploy or restore the Supabase project to activate the worker."
        )

    # 6. Pre-initialise OAuth state storage singleton (logs which backend was selected)
    OAuthStateStorageFactory.create()

    logger.info("DevBrain API started")


@app.on_event("shutdown")
async def shutdown_event() -> None:
    global _stop_event, _worker_task
    
    # Stop worker loop
    if _stop_event:
        _stop_event.set()
    if _worker_task:
        try:
            await asyncio.wait_for(_worker_task, timeout=10.0)
        except asyncio.TimeoutError:
            _worker_task.cancel()
    
    await close_redis()
    await shutdown_oauth_state_storage()
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
