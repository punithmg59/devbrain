import logging

import sentry_sdk
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sentry_sdk.integrations.fastapi import FastApiIntegration

from app.config import get_settings
from app.database import init_db, test_connection
from app.routers import analysis, auth, repo_detail, repos
from app.utils.errors import DevBrainException
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


@app.exception_handler(DevBrainException)
async def devbrain_exception_handler(request: Request, exc: DevBrainException) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.message, "code": exc.code},
    )


@app.on_event("startup")
async def startup_event() -> None:
    try:
        await init_redis()
    except Exception as e:
        logger.error("Failed to initialize Redis: %s", e)
    try:
        await init_db()
    except Exception as e:
        logger.error("Failed to initialize database tables: %s", e)
    logger.info("DevBrain API started")
    connected = await test_connection()
    if connected:
        logger.info("Database: connected")
    else:
        logger.warning("Database: connection failed")


@app.on_event("shutdown")
async def shutdown_event() -> None:
    await close_redis()
    logger.info("DevBrain API shutting down")


@app.get("/health")
async def health_check():
    connected = await test_connection()
    return {
        "status": "healthy",
        "environment": settings.environment,
        "database": "connected" if connected else "disconnected",
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
