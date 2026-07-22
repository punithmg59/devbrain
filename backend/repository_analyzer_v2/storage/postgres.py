import asyncio
import logging
from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator, Dict, Optional

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from config.settings import AnalyzerSettings, get_settings
from utils.exceptions import ErrorCode, StorageError

logger = logging.getLogger(__name__)


class DatabaseManager:
    """
    Manages async SQLAlchemy engine, connection pooling, health checking,
    retry mechanism, and session factory for PostgreSQL (and SQLite in tests).
    """

    def __init__(self, settings: Optional[AnalyzerSettings] = None) -> None:
        self._settings = settings
        self._engine: Optional[AsyncEngine] = None
        self._session_factory: Optional[async_sessionmaker[AsyncSession]] = None
        self._init_lock: asyncio.Lock = asyncio.Lock()

    @property
    def settings(self) -> AnalyzerSettings:
        if self._settings is None:
            self._settings = get_settings()
        return self._settings

    def _normalize_db_url(self, db_url: str) -> str:
        """Ensure the database URL uses an async driver."""
        if db_url.startswith("postgresql://"):
            return db_url.replace("postgresql://", "postgresql+asyncpg://", 1)
        elif db_url.startswith("postgres://"):
            return db_url.replace("postgres://", "postgresql+asyncpg://", 1)
        elif db_url.startswith("sqlite://") and not db_url.startswith("sqlite+aiosqlite://"):
            return db_url.replace("sqlite://", "sqlite+aiosqlite://", 1)
        return db_url

    async def initialize(
        self,
        pool_size: int = 10,
        max_overflow: int = 20,
        pool_recycle: int = 3600,
        pool_pre_ping: bool = True,
        custom_url: Optional[str] = None,
    ) -> None:
        """Initialize the async SQLAlchemy engine and session factory."""
        async with self._init_lock:
            if self._engine is not None:
                return

            raw_url = custom_url or self.settings.database_url
            db_url = self._normalize_db_url(raw_url)

            engine_kwargs: Dict[str, Any] = {
                "echo": self.settings.debug_mode,
                "future": True,
            }

            # Configure connection pool settings (for non-sqlite databases)
            if "sqlite" not in db_url:
                engine_kwargs.update({
                    "pool_size": pool_size,
                    "max_overflow": max_overflow,
                    "pool_recycle": pool_recycle,
                    "pool_pre_ping": pool_pre_ping,
                })

            try:
                self._engine = create_async_engine(db_url, **engine_kwargs)
                self._session_factory = async_sessionmaker(
                    bind=self._engine,
                    class_=AsyncSession,
                    expire_on_commit=False,
                    autoflush=False,
                )
                safe_url = db_url.split("@")[-1] if "@" in db_url else db_url
                logger.info(f"Database engine initialized for URL pattern '{safe_url}'")
            except Exception as e:
                logger.error(f"Failed to create database engine: {e}")
                raise StorageError(
                    f"Failed to initialize database engine: {e}",
                    code=ErrorCode.STORAGE_CONNECTION,
                    cause=e,
                ) from e

    async def connect_with_retry(
        self,
        max_retries: int = 3,
        initial_delay: float = 0.1,
        backoff_factor: float = 2.0,
        custom_url: Optional[str] = None,
    ) -> bool:
        """
        Attempts to initialize and verify connection with exponential backoff retries.
        """
        if self._engine is None:
            await self.initialize(custom_url=custom_url)

        delay = initial_delay
        last_error: Optional[Exception] = None

        for attempt in range(1, max_retries + 1):
            try:
                is_healthy = await self.health_check()
                if is_healthy:
                    logger.info(f"Database connection verified healthy on attempt {attempt}.")
                    return True
            except Exception as e:
                last_error = e
                logger.warning(f"Database connection attempt {attempt}/{max_retries} failed: {e}")

            if attempt < max_retries:
                await asyncio.sleep(delay)
                delay *= backoff_factor

        msg = f"Failed to connect to database after {max_retries} retries"
        logger.error(msg)
        raise StorageError(
            msg,
            code=ErrorCode.STORAGE_CONNECTION,
            cause=last_error,
        )

    async def health_check(self) -> bool:
        """
        Executes a lightweight query (SELECT 1) asynchronously to verify connection health.
        """
        if self._engine is None:
            return False

        try:
            async with self._engine.connect() as conn:
                result = await conn.execute(text("SELECT 1"))
                return result.scalar() == 1
        except Exception as e:
            logger.warning(f"Database health check failed: {e}")
            return False

    @asynccontextmanager
    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        """Async context manager providing a transactional AsyncSession."""
        if self._session_factory is None:
            raise StorageError(
                "DatabaseManager is not initialized. Call initialize() or connect_with_retry() first.",
                code=ErrorCode.STORAGE_CONNECTION,
            )

        async with self._session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception as e:
                await session.rollback()
                logger.error(f"Database session transaction error, rolled back: {e}")
                raise StorageError(
                    f"Database transaction error: {e}",
                    code=ErrorCode.STORAGE_WRITE_FAILED,
                    cause=e,
                ) from e

    async def close(self) -> None:
        """Disposes the async engine cleanly."""
        async with self._init_lock:
            if self._engine is not None:
                await self._engine.dispose()
                self._engine = None
                self._session_factory = None
                logger.info("Database engine disposed.")
