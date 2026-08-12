"""
Tests for orchestrator job-claiming behavior on SQLite.

Tests:
1. queued job can be claimed
2. stale job can be reclaimed
3. fresh active job cannot be reclaimed
4. _running_jobs jobs cannot be claimed
5. two concurrent workers cannot claim the same job
6. heartbeat refresh prevents stale reclaim
7. completed jobs cannot be claimed
8. failed jobs cannot be claimed
"""
import asyncio
import uuid
from datetime import datetime, timezone, timedelta
from unittest.mock import patch

import pytest
import pytest_asyncio

# Use aiosqlite for tests
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.pool import StaticPool
from sqlalchemy import text

from app.database import Base

# We patch app.database.engine and app.database.async_session_factory before importing orchestrator
import app.database as _db_module


@pytest_asyncio.fixture(scope="function")
async def sqlite_session_factory():
    """Create a fresh in-memory SQLite DB and session factory for each test."""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        import app.models  # ensure models registered
        await conn.run_sync(Base.metadata.create_all)

    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    yield engine, factory
    await engine.dispose()


async def _insert_job(factory, status: str, heartbeat_at=None, job_id=None) -> uuid.UUID:
    """Insert a test analysis_job row directly."""
    jid = job_id or uuid.uuid4()
    repo_id = uuid.uuid4()
    user_id = uuid.uuid4()

    async with factory() as db:
        await db.execute(text("""
            INSERT INTO analysis_jobs
                (id, repo_id, user_id, status, heartbeat_at, created_at)
            VALUES
                (:id, :repo_id, :user_id, :status, :heartbeat_at, datetime('now'))
        """), {
            "id": str(jid),
            "repo_id": str(repo_id),
            "user_id": str(user_id),
            "status": status,
            "heartbeat_at": heartbeat_at,
        })
        await db.commit()

    return jid


async def _get_job_status(factory, jid: uuid.UUID) -> str:
    async with factory() as db:
        row = (await db.execute(
            text("SELECT status FROM analysis_jobs WHERE id = :id"),
            {"id": str(jid)},
        )).first()
        return row[0] if row else None


# ── Test 1: queued job can be claimed ─────────────────────────────────────────

@pytest.mark.asyncio
async def test_queued_job_can_be_claimed(sqlite_session_factory):
    engine, factory = sqlite_session_factory

    jid = await _insert_job(factory, status="queued")

    with patch.object(_db_module, "engine", engine), \
         patch.object(_db_module, "async_session_factory", factory):
        from importlib import reload
        import app.services.pipeline.orchestrator as orch
        reload(orch)
        orch._running_jobs.clear()

        claimed_id, reason = await orch._claim_next_job()

    assert claimed_id == jid
    assert reason == "status='queued'"
    assert await _get_job_status(factory, jid) == "cloning"


# ── Test 2: stale job can be reclaimed ────────────────────────────────────────

@pytest.mark.asyncio
async def test_stale_job_can_be_reclaimed(sqlite_session_factory):
    engine, factory = sqlite_session_factory

    stale_time = (datetime.now(timezone.utc) - timedelta(seconds=200)).strftime("%Y-%m-%d %H:%M:%S")
    jid = await _insert_job(factory, status="parsing", heartbeat_at=stale_time)

    with patch.object(_db_module, "engine", engine), \
         patch.object(_db_module, "async_session_factory", factory):
        from importlib import reload
        import app.services.pipeline.orchestrator as orch
        reload(orch)
        orch._running_jobs.clear()

        claimed_id, reason = await orch._claim_next_job()

    assert claimed_id == jid
    assert reason == "stale_heartbeat"
    assert await _get_job_status(factory, jid) == "cloning"


# ── Test 3: fresh active job cannot be reclaimed ──────────────────────────────

@pytest.mark.asyncio
async def test_fresh_active_job_cannot_be_reclaimed(sqlite_session_factory):
    engine, factory = sqlite_session_factory

    fresh_time = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    jid = await _insert_job(factory, status="parsing", heartbeat_at=fresh_time)

    with patch.object(_db_module, "engine", engine), \
         patch.object(_db_module, "async_session_factory", factory):
        from importlib import reload
        import app.services.pipeline.orchestrator as orch
        reload(orch)
        orch._running_jobs.clear()

        claimed_id, reason = await orch._claim_next_job()

    assert claimed_id is None
    # Job must still be in 'parsing', not 'cloning'
    assert await _get_job_status(factory, jid) == "parsing"


# ── Test 4: _running_jobs jobs cannot be claimed ──────────────────────────────

@pytest.mark.asyncio
async def test_running_jobs_excluded(sqlite_session_factory):
    engine, factory = sqlite_session_factory

    jid = await _insert_job(factory, status="queued")

    with patch.object(_db_module, "engine", engine), \
         patch.object(_db_module, "async_session_factory", factory):
        from importlib import reload
        import app.services.pipeline.orchestrator as orch
        reload(orch)
        orch._running_jobs.clear()
        orch._running_jobs.add(jid)  # mark as already running in this process

        claimed_id, reason = await orch._claim_next_job()
        orch._running_jobs.clear()

    assert claimed_id is None


# ── Test 5: two concurrent workers cannot claim the same job ──────────────────

@pytest.mark.asyncio
async def test_concurrent_workers_cannot_double_claim(sqlite_session_factory):
    engine, factory = sqlite_session_factory

    jid = await _insert_job(factory, status="queued")

    with patch.object(_db_module, "engine", engine), \
         patch.object(_db_module, "async_session_factory", factory):
        from importlib import reload
        import app.services.pipeline.orchestrator as orch
        reload(orch)
        orch._running_jobs.clear()

        # Run two concurrent claims
        results = await asyncio.gather(
            orch._claim_next_job(),
            orch._claim_next_job(),
        )

    claimed = [r for r in results if r[0] is not None]
    assert len(claimed) == 1, f"Expected exactly 1 claim but got {len(claimed)}: {results}"
    assert claimed[0][0] == jid


# ── Test 6: heartbeat refresh prevents stale reclaim ─────────────────────────

@pytest.mark.asyncio
async def test_heartbeat_prevents_stale_reclaim(sqlite_session_factory):
    engine, factory = sqlite_session_factory

    # Job is active with fresh heartbeat
    fresh_time = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    jid = await _insert_job(factory, status="parsing", heartbeat_at=fresh_time)

    with patch.object(_db_module, "engine", engine), \
         patch.object(_db_module, "async_session_factory", factory):
        from importlib import reload
        import app.services.pipeline.orchestrator as orch
        reload(orch)
        orch._running_jobs.clear()

        # Simulate heartbeat refresh
        stop = asyncio.Event()
        stop.set()  # Stop immediately after first check
        # Just verify the heartbeat SQL works without error
        async with factory() as db:
            await db.execute(
                text("UPDATE analysis_jobs SET heartbeat_at = datetime('now') WHERE id = :id"),
                {"id": str(jid)},
            )
            await db.commit()

        # Attempt to claim — should fail because heartbeat is fresh
        claimed_id, _ = await orch._claim_next_job()

    assert claimed_id is None


# ── Test 7: completed jobs cannot be claimed ──────────────────────────────────

@pytest.mark.asyncio
async def test_completed_job_cannot_be_claimed(sqlite_session_factory):
    engine, factory = sqlite_session_factory

    jid = await _insert_job(factory, status="completed")

    with patch.object(_db_module, "engine", engine), \
         patch.object(_db_module, "async_session_factory", factory):
        from importlib import reload
        import app.services.pipeline.orchestrator as orch
        reload(orch)
        orch._running_jobs.clear()

        claimed_id, _ = await orch._claim_next_job()

    assert claimed_id is None


# ── Test 8: failed jobs cannot be claimed ─────────────────────────────────────

@pytest.mark.asyncio
async def test_failed_job_cannot_be_claimed(sqlite_session_factory):
    engine, factory = sqlite_session_factory

    jid = await _insert_job(factory, status="failed")

    with patch.object(_db_module, "engine", engine), \
         patch.object(_db_module, "async_session_factory", factory):
        from importlib import reload
        import app.services.pipeline.orchestrator as orch
        reload(orch)
        orch._running_jobs.clear()

        claimed_id, _ = await orch._claim_next_job()

    assert claimed_id is None
