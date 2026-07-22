import asyncio
import pytest
import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from storage import DatabaseManager
from utils.exceptions import StorageError


TEST_DB_URL = "sqlite+aiosqlite:///:memory:"


@pytest_asyncio.fixture
async def db_manager():
    manager = DatabaseManager()
    await manager.initialize(custom_url=TEST_DB_URL)
    yield manager
    await manager.close()


@pytest.mark.asyncio
async def test_database_initialization(db_manager):
    """Test initializing DatabaseManager with custom URL."""
    assert db_manager._engine is not None
    assert db_manager._session_factory is not None


@pytest.mark.asyncio
async def test_health_check_success(db_manager):
    """Test health check returns True for a valid connection."""
    is_healthy = await db_manager.health_check()
    assert is_healthy is True


@pytest.mark.asyncio
async def test_health_check_uninitialized():
    """Test health check returns False when DatabaseManager is uninitialized."""
    manager = DatabaseManager()
    assert await manager.health_check() is False


@pytest.mark.asyncio
async def test_connect_with_retry_success():
    """Test connect_with_retry initializes and verifies healthy connection."""
    manager = DatabaseManager()
    success = await manager.connect_with_retry(
        max_retries=2, initial_delay=0.01, custom_url=TEST_DB_URL
    )
    assert success is True
    assert await manager.health_check() is True
    await manager.close()


@pytest.mark.asyncio
async def test_connect_with_retry_failure():
    """Test connect_with_retry raises StorageError on invalid connection string."""
    manager = DatabaseManager()
    with pytest.raises(StorageError, match="Failed to connect"):
        await manager.connect_with_retry(
            max_retries=2,
            initial_delay=0.01,
            custom_url="postgresql+asyncpg://invalid_user:invalid_pass@127.0.0.1:9999/nonexistent_db",
        )
    await manager.close()


@pytest.mark.asyncio
async def test_get_session_transaction(db_manager):
    """Test executing a query using AsyncSession context manager."""
    async with db_manager.get_session() as session:
        assert isinstance(session, AsyncSession)
        result = await session.execute(text("SELECT 42"))
        val = result.scalar()
        assert val == 42


@pytest.mark.asyncio
async def test_get_session_rollback_on_error(db_manager):
    """Test transaction rollback and StorageError exception on error inside session."""
    with pytest.raises(StorageError, match="Database transaction error"):
        async with db_manager.get_session() as session:
            await session.execute(text("SELECT * FROM non_existent_table"))


@pytest.mark.asyncio
async def test_uninitialized_session_raises():
    """Test acquiring session from uninitialized DatabaseManager raises StorageError."""
    manager = DatabaseManager()
    with pytest.raises(StorageError, match="not initialized"):
        async with manager.get_session():
            pass


@pytest.mark.asyncio
async def test_close_disposes_engine(db_manager):
    """Test close() disposes the engine and clears state."""
    await db_manager.close()
    assert db_manager._engine is None
    assert db_manager._session_factory is None
    assert await db_manager.health_check() is False
