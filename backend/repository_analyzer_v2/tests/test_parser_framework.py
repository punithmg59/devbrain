"""
tests/test_parser_framework.py
-------------------------------
Comprehensive unit, stress, concurrency, and validation tests for Phase 3.9 — Parser Testing Framework.
"""

from __future__ import annotations

import asyncio
import pytest

from core.parser_manager import ParserManager
from core.parser_registry import ParserRegistry
from models.parser import ParserError, ParserLanguage, ParserResult, ParserStatus
from plugins.parser_plugin import ParserPlugin
from utils.exceptions import PluginError
from utils.parser_testing import (
    BrokenParserPlugin,
    ConfigurableMockParserPlugin,
    InvalidParserPlugin,
    ParserTestHarness,
    SlowParserPlugin,
    TimeoutParserPlugin,
)


@pytest.fixture(autouse=True)
def reset_framework_singletons():
    """Reset ParserManager and ParserRegistry singletons before and after each test."""
    ParserManager.reset()
    ParserRegistry.reset()
    yield
    ParserManager.reset()
    ParserRegistry.reset()


# ---------------------------------------------------------------------------
# Mock & Special Plugin Tests
# ---------------------------------------------------------------------------

def test_configurable_mock_parser_plugin():
    err = ParserError(message="Syntax error at line 5")
    plugin = ConfigurableMockParserPlugin(
        target_language=ParserLanguage.PYTHON,
        return_status=ParserStatus.SYNTAX_ERROR,
        errors=[err],
    )
    plugin.initialize()

    job = ParserTestHarness.create_job("src/test.py", "python")
    ctx = ParserTestHarness.create_context(job)

    res = plugin.parse(job, ctx)
    assert res.status == ParserStatus.SYNTAX_ERROR
    assert len(res.errors) == 1
    assert res.errors[0].message == "Syntax error at line 5"


@pytest.mark.asyncio
async def test_broken_parser_plugin_fault_isolation():
    pm = ParserManager.get_instance()
    broken_plugin = BrokenParserPlugin(
        target_language=ParserLanguage.PYTHON,
        exception_factory=ValueError,
    )
    pm.register_parser(broken_plugin)

    job = ParserTestHarness.create_job("src/fail.py", "python")
    ctx = ParserTestHarness.create_context(job)

    res = await pm.execute_parser(job, ctx)
    assert res.status == ParserStatus.INTERNAL_ERROR
    assert len(res.errors) == 1
    assert "Simulated crash in BrokenParserPlugin" in res.errors[0].message


@pytest.mark.asyncio
async def test_slow_parser_plugin_execution():
    pm = ParserManager.get_instance()
    slow_plugin = SlowParserPlugin(
        target_language=ParserLanguage.TYPESCRIPT,
        delay_seconds=0.01,
    )
    pm.register_parser(slow_plugin)

    job = ParserTestHarness.create_job("src/slow.ts", "typescript")
    ctx = ParserTestHarness.create_context(job)

    res = await pm.execute_parser(job, ctx)
    assert res.status == ParserStatus.SUCCESS
    assert res.statistics.duration_ms >= 10.0


@pytest.mark.asyncio
async def test_timeout_parser_plugin_cancellation():
    pm = ParserManager.get_instance()
    timeout_plugin = TimeoutParserPlugin(
        target_language=ParserLanguage.GO,
        sleep_duration_seconds=2.0,
    )
    pm.register_parser(timeout_plugin)

    job = ParserTestHarness.create_job("src/main.go", "go")
    ctx = ParserTestHarness.create_context(job)
    ctx.cancellation_token.cancel()  # Trigger cancellation

    with pytest.raises(asyncio.CancelledError):
        await pm.execute_parser(job, ctx)


# ---------------------------------------------------------------------------
# Plugin Validation Tests
# ---------------------------------------------------------------------------

def test_invalid_parser_plugin_rejection():
    pm = ParserManager.get_instance()
    reg = ParserRegistry.get_instance()
    invalid_obj = InvalidParserPlugin()

    with pytest.raises(PluginError):
        pm.register_parser(invalid_obj)  # type: ignore[arg-type]

    with pytest.raises(PluginError):
        reg.register(invalid_obj)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Stress & Concurrency Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_stress_test_harness():
    pm = ParserManager.get_instance()
    mock_plugin = ConfigurableMockParserPlugin(target_language=ParserLanguage.PYTHON)
    pm.register_parser(mock_plugin)

    summary = await ParserTestHarness.run_stress_test(
        manager=pm,
        job_count=50,
        language="python",
    )

    assert summary["job_count"] == 50
    assert summary["completed"] == 50
    assert summary["successes"] == 50
    assert summary["throughput_jobs_per_sec"] > 0.0


@pytest.mark.asyncio
async def test_concurrent_async_parsing():
    pm = ParserManager.get_instance()
    mock_plugin = ConfigurableMockParserPlugin(target_language=ParserLanguage.PYTHON)
    pm.register_parser(mock_plugin)

    async def parse_worker(worker_idx: int):
        for i in range(10):
            job = ParserTestHarness.create_job(f"src/worker_{worker_idx}_file_{i}.py", "python")
            ctx = ParserTestHarness.create_context(job, run_id=f"run-worker-{worker_idx}")
            res = await pm.execute_parser(job, ctx)
            assert res.status == ParserStatus.SUCCESS

    workers = [parse_worker(idx) for idx in range(5)]
    await asyncio.gather(*workers)
