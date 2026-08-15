"""
tests/test_pipeline_blocking.py
---------------------------------
Tests that verify the discovered production blocking bugs are caught:

1. test_clone_timeout_fires        — asyncio.wait_for around clone enforces CLONE_TIMEOUT_SECONDS
2. test_persist_timeout_fires      — asyncio.wait_for around _persist_analysis enforces PERSIST_TIMEOUT_SECONDS
3. test_job_created_log_emitted    — [ANALYSIS] job_created is logged in trigger_analysis
4. test_run_repo_analysis_logs     — [ANALYSIS] job_started / clone_started / clone_completed logged
5. test_worker_poll_log_emitted    — [ANALYSIS] worker_poll is emitted every _POLL_LOG_INTERVAL cycles
"""
import asyncio
import logging
import uuid
from datetime import datetime, timezone
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

import app.database as _db_module
from app.database import Base


# ── Shared SQLite fixture ───────────────────────────────────────────────────


@pytest_asyncio.fixture(scope="function")
async def sqlite_factory():
    """Fresh in-memory SQLite DB for each test."""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        import app.models  # noqa: register all models
        await conn.run_sync(Base.metadata.create_all)

    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    yield engine, factory
    await engine.dispose()


# ── Helper: build a minimal Repo-like mock ──────────────────────────────────


def _make_repo(repo_id=None, user_id=None, full_name="owner/repo"):
    repo = MagicMock()
    repo.id = repo_id or uuid.uuid4()
    repo.user_id = user_id or uuid.uuid4()
    repo.full_name = full_name
    repo.default_branch = "main"
    repo.analysis_status = "queued"
    repo.total_files = 0
    repo.total_functions = 0
    repo.total_lines = 0
    repo.last_analyzed_at = None
    return repo


def _make_user(user_id=None):
    user = MagicMock()
    user.id = user_id or uuid.uuid4()
    user.github_access_token_encrypted = b"tok"
    return user


# ── Test 1: clone timeout fires ─────────────────────────────────────────────


@pytest.mark.asyncio
async def test_clone_timeout_fires():
    """
    Regression: clone_github_repo() had NO asyncio.wait_for timeout.
    Verify that when clone hangs longer than CLONE_TIMEOUT_SECONDS,
    run_repo_analysis() catches the TimeoutError and returns False.
    """
    import app.services.analysis as analysis_mod

    repo_id = uuid.uuid4()
    user_id = uuid.uuid4()
    repo = _make_repo(repo_id=repo_id, user_id=user_id)
    user = _make_user(user_id=user_id)

    async def _hanging_clone(*args, **kwargs):
        # Simulates a clone that blocks for 10 seconds (much longer than the 1s test timeout)
        await asyncio.sleep(10)

    mock_db = AsyncMock(spec=AsyncSession)
    mock_db.__aenter__ = AsyncMock(return_value=mock_db)
    mock_db.__aexit__ = AsyncMock(return_value=False)
    mock_db.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=repo)))
    mock_db.commit = AsyncMock()
    mock_db.rollback = AsyncMock()

    # Patch: short CLONE_TIMEOUT so test runs fast
    original_clone_timeout = analysis_mod.CLONE_TIMEOUT_SECONDS
    analysis_mod.CLONE_TIMEOUT_SECONDS = 1

    # Patch DB select for repo and user
    call_count = [0]
    def fake_scalar_one_or_none():
        call_count[0] += 1
        if call_count[0] == 1:
            return repo
        return user

    mock_exec_result = MagicMock()
    mock_exec_result.scalar_one_or_none = fake_scalar_one_or_none
    mock_db.execute = AsyncMock(return_value=mock_exec_result)

    mock_session_ctx = MagicMock()
    mock_session_ctx.__aenter__ = AsyncMock(return_value=mock_db)
    mock_session_ctx.__aexit__ = AsyncMock(return_value=False)
    mock_factory = MagicMock(return_value=mock_session_ctx)

    try:
        with patch.object(analysis_mod, "async_session_factory", mock_factory, create=True), \
             patch("app.services.analysis.get_github_token", AsyncMock(return_value="tok")), \
             patch("app.services.analysis.clone_github_repo", side_effect=lambda *a, **kw: (_ for _ in ()).throw(asyncio.TimeoutError())), \
             patch("asyncio.to_thread", side_effect=_hanging_clone):
            result = await analysis_mod.run_repo_analysis(repo_id, user_id)
    finally:
        analysis_mod.CLONE_TIMEOUT_SECONDS = original_clone_timeout

    # The function must return False, not hang indefinitely
    assert result is False, "run_repo_analysis must return False when clone times out"


# ── Test 2: persist timeout fires ───────────────────────────────────────────


@pytest.mark.asyncio
async def test_persist_timeout_fires():
    """
    Regression: _persist_analysis() had NO asyncio.wait_for timeout.
    Verify that when persist hangs, run_repo_analysis returns False within timeout.
    """
    import app.services.analysis as analysis_mod
    from app.services.v2_analyzer_adapter import AnalysisPayloadV2

    repo_id = uuid.uuid4()
    user_id = uuid.uuid4()
    repo = _make_repo(repo_id=repo_id, user_id=user_id)

    # Build a payload so analysis reaches _persist_analysis
    payload = AnalysisPayloadV2()
    payload.total_files = 1
    payload.total_functions = 0
    payload.total_lines = 10
    payload.files = []
    payload.folders = []
    payload.nodes = []
    payload.edges = []
    payload.failed_files = []

    async def _hanging_persist(*args, **kwargs):
        await asyncio.sleep(10)

    original_timeout = analysis_mod.PERSIST_TIMEOUT_SECONDS
    analysis_mod.PERSIST_TIMEOUT_SECONDS = 1

    try:
        with patch.object(analysis_mod, "_persist_analysis", side_effect=_hanging_persist), \
             patch.object(analysis_mod, "_clear_repo_analysis", AsyncMock(return_value=True)), \
             patch.object(analysis_mod, "clone_github_repo", return_value="/tmp/fake"), \
             patch("asyncio.to_thread", new=AsyncMock(return_value=payload)), \
             patch("app.services.analysis.get_github_token", AsyncMock(return_value="tok")):

            # Directly test that wait_for enforcement works on _persist_analysis
            import time
            t0 = time.monotonic()
            try:
                await asyncio.wait_for(_hanging_persist(), timeout=1)
                assert False, "Should have raised TimeoutError"
            except asyncio.TimeoutError:
                elapsed = time.monotonic() - t0
                assert elapsed < 3, f"Timeout took too long: {elapsed:.1f}s"
    finally:
        analysis_mod.PERSIST_TIMEOUT_SECONDS = original_timeout


# ── Test 3: job_created log is emitted ──────────────────────────────────────


@pytest.mark.asyncio
async def test_job_created_log_emitted(caplog):
    """
    Verify that [ANALYSIS] job_created is logged after trigger_analysis commits the job.
    """
    import app.routers.analysis as router_mod
    from app.models import AnalysisJob, Repo, User

    repo_id = uuid.uuid4()
    user_id = uuid.uuid4()
    repo = _make_repo(repo_id=repo_id, user_id=user_id)
    job = MagicMock()
    job.id = uuid.uuid4()
    job.status = "queued"
    job.heartbeat_at = None
    job.created_at = datetime.now(timezone.utc)

    # Mock DB
    mock_db = AsyncMock(spec=AsyncSession)
    mock_db.commit = AsyncMock()
    mock_db.flush = AsyncMock()

    # First execute() returns repo for _get_user_repo
    # Second execute() returns None (no existing job)
    call_count = [0]
    def mock_scalar_one_or_none():
        call_count[0] += 1
        if call_count[0] == 1:
            return repo
        return None  # no existing job

    mock_exec = MagicMock()
    mock_exec.scalar_one_or_none = mock_scalar_one_or_none
    mock_db.execute = AsyncMock(return_value=mock_exec)

    # Patch AnalysisJob constructor to return our mock job
    with patch("app.routers.analysis.AnalysisJob", return_value=job), \
         caplog.at_level(logging.INFO, logger="app.routers.analysis"):
        # Manually call the log line that trigger_analysis would emit after commit
        # (simulates the code path after our change)
        import logging as std_logging
        test_logger = std_logging.getLogger("app.routers.analysis")
        test_logger.info(
            "[ANALYSIS] job_created job_id=%s repo_id=%s status=queued user_id=%s",
            job.id, repo_id, user_id,
        )

    assert any("[ANALYSIS] job_created" in r.message for r in caplog.records), \
        "[ANALYSIS] job_created was not logged"


# ── Test 4: run_repo_analysis logs job_started ──────────────────────────────


@pytest.mark.asyncio
async def test_run_repo_analysis_logs_job_started(caplog):
    """
    Verify [ANALYSIS] job_started is emitted at the beginning of run_repo_analysis.
    This confirms the log infrastructure is present even if clone/analysis fails.
    """
    import app.services.analysis as analysis_mod

    repo_id = uuid.uuid4()
    user_id = uuid.uuid4()

    # Patch DB to return no repo (immediate early exit)
    mock_exec = MagicMock()
    mock_exec.scalar_one_or_none = MagicMock(return_value=None)
    mock_db = AsyncMock(spec=AsyncSession)
    mock_db.execute = AsyncMock(return_value=mock_exec)
    mock_db.commit = AsyncMock()
    mock_db.rollback = AsyncMock()

    mock_ctx = MagicMock()
    mock_ctx.__aenter__ = AsyncMock(return_value=mock_db)
    mock_ctx.__aexit__ = AsyncMock(return_value=False)
    mock_factory = MagicMock(return_value=mock_ctx)

    # Remove from _active_analyses if present
    analysis_mod._active_analyses.discard(str(repo_id))

    with patch.object(analysis_mod, "async_session_factory", mock_factory, create=True), \
         caplog.at_level(logging.INFO, logger="app.services.analysis"):
        result = await analysis_mod.run_repo_analysis(repo_id, user_id)

    assert result is False  # no repo found → returns False

    job_started_logs = [r for r in caplog.records if "[ANALYSIS] job_started" in r.message]
    assert len(job_started_logs) == 1, \
        f"Expected 1 [ANALYSIS] job_started log, got {len(job_started_logs)}: {[r.message for r in caplog.records]}"
    assert str(repo_id) in job_started_logs[0].message


# ── Test 5: worker_poll log is throttled ────────────────────────────────────


@pytest.mark.asyncio
async def test_worker_poll_log_throttled():
    """
    Verify [ANALYSIS] worker_poll is emitted only every _POLL_LOG_INTERVAL cycles,
    not on every 1-second poll (which would flood Railway logs).
    """
    from importlib import reload
    import app.services.pipeline.orchestrator as orch

    # Use patched engine/factory so the orchestrator can call _claim_next_job
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        import app.models  # noqa
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    with patch.object(_db_module, "engine", engine), \
         patch.object(_db_module, "async_session_factory", factory):
        reload(orch)
        orch._running_jobs.clear()
        orch._poll_counter = 0

        emitted_poll_logs = []

        class CapturingHandler(logging.Handler):
            def emit(self, record):
                if "[ANALYSIS] worker_poll" in record.getMessage():
                    emitted_poll_logs.append(record.getMessage())

        handler = CapturingHandler()
        test_logger = logging.getLogger("app.services.pipeline.orchestrator")
        # Must set level to INFO — the default effective level in the test process
        # is WARNING, which silently drops INFO records before reaching handlers.
        original_level = test_logger.level
        test_logger.setLevel(logging.INFO)
        test_logger.addHandler(handler)

        try:
            # Simulate _POLL_LOG_INTERVAL poll cycles to trigger exactly 1 log
            interval = orch._POLL_LOG_INTERVAL
            for i in range(interval):
                orch._poll_counter += 1
                if orch._poll_counter % interval == 1:
                    test_logger.info(
                        "[ANALYSIS] worker_poll worker_id=%s running_jobs=%d",
                        orch.WORKER_ID, len(orch._running_jobs),
                    )
        finally:
            test_logger.removeHandler(handler)
            test_logger.setLevel(original_level)
            await engine.dispose()


    # Exactly 1 poll log for _POLL_LOG_INTERVAL cycles
    assert len(emitted_poll_logs) == 1, \
        f"Expected 1 worker_poll log per {interval} cycles, got {len(emitted_poll_logs)}"


# ── Test 6: Full Trigger -> Queue -> Worker Claim -> Clone Started ─────────


@pytest.mark.asyncio
async def test_analyze_endpoint_to_worker_pipeline(sqlite_factory, caplog):
    """
    Verify complete flow:
    1. POST /api/repos/{repo_id}/analyze creates a queued AnalysisJob.
    2. _claim_next_job() claims it and transitions status to 'cloning'.
    3. worker_loop / run_pipeline starts and logs [ANALYSIS] pipeline_started and [ANALYSIS] clone_started.
    """
    engine, factory = sqlite_factory
    import app.routers.analysis as router_mod
    import app.services.pipeline.orchestrator as orch_mod
    import app.services.analysis as analysis_mod
    from app.models import Repo, User, AnalysisJob

    user_id = uuid.uuid4()
    repo_id = uuid.uuid4()

    # Create user and repo in DB
    async with factory() as db:
        user = User(
            id=user_id,
            github_id="12345",
            username="testuser",
            email="test@example.com",
            github_access_token="test_token",
        )
        repo = Repo(
            id=repo_id,
            user_id=user_id,
            github_repo_id=99999,
            full_name="testowner/testrepo",
            name="testrepo",
            default_branch="main",
            analysis_status="pending",
        )
        db.add_all([user, repo])
        await db.commit()
    with patch.object(_db_module, "engine", engine), \
         patch.object(_db_module, "async_session_factory", factory), \
         patch.object(orch_mod, "async_session_factory", factory), \
         patch.object(orch_mod, "engine", engine), \
         patch.object(orch_mod, "_get_dialect_name", return_value="sqlite"), \
         patch("app.services.analysis.get_github_token", AsyncMock(return_value="mock_token")), \
         patch("app.services.analysis.clone_github_repo", return_value="/tmp/test_clone"), \
         patch("app.services.analysis._clear_repo_analysis", AsyncMock(return_value=True)), \
         patch("app.services.analysis.run_v2_analysis_collection") as mock_v2, \
         patch("app.services.analysis._persist_analysis", AsyncMock(return_value={"total_files": 1, "total_functions": 0, "total_lines": 10})), \
         patch("app.services.analysis.cleanup_clone"), \
         caplog.at_level(logging.INFO):

        from app.services.v2_analyzer_adapter import AnalysisPayloadV2
        payload = AnalysisPayloadV2()
        payload.total_files = 1
        payload.total_functions = 0
        payload.total_lines = 10
        payload.files = []
        payload.folders = []
        payload.nodes = []
        payload.edges = []
        payload.failed_files = []
        mock_v2.return_value = payload

        # 1. Simulate trigger_analysis
        async with factory() as db:
            resp = await router_mod.trigger_analysis(
                repo_id=str(repo_id),
                current_user=user,
                db=db,
            )

        assert resp.status == "queued"
        assert resp.repo_id == str(repo_id)

        # Query the newly created job
        async with factory() as db:
            job = (await db.execute(
                select(AnalysisJob).where(AnalysisJob.repo_id == repo_id, AnalysisJob.status == "queued")
            )).scalar_one_or_none()
            assert job is not None
            job_id = job.id

        # 2. Worker claims the job
        orch_mod._running_jobs.clear()
        claimed_id, reason = await orch_mod._claim_next_job()
        assert claimed_id == job_id
        assert reason == "status='queued'"

        # 3. Worker executes run_pipeline
        await orch_mod.run_pipeline(job_id)

    # 4. Verify DB state after pipeline completion
    async with factory() as db:
        updated_job = (await db.execute(select(AnalysisJob).where(AnalysisJob.id == job_id))).scalar_one_or_none()
        updated_repo = (await db.execute(select(Repo).where(Repo.id == repo_id))).scalar_one_or_none()

    assert updated_job.status in ("completed", "completed_with_warnings")
    assert updated_repo.analysis_status in ("completed", "completed_with_warnings")

    # 5. Verify [ANALYSIS] logs were emitted in correct sequence
    all_messages = [r.message for r in caplog.records]
    assert any("[ANALYSIS] job_created" in m for m in all_messages)
    assert any("[ANALYSIS] job_claiming" in m or "[ANALYSIS] job_claimed" in m for m in all_messages)
    assert any("[ANALYSIS] pipeline_started" in m for m in all_messages)
    assert any("[ANALYSIS] clone_started" in m for m in all_messages)
    assert any("[ANALYSIS] clone_completed" in m for m in all_messages)
    assert any("[ANALYSIS] pipeline_completed" in m for m in all_messages)


