"""
pipeline/parser.py
------------------
Phase 3.7 — Parser Stage with ParserManager Integration.

Upgrades the ParserStage to route each AnalysisJob through:

    Worker → ExecutionContext → ParserManager → ParserPlugin → ParserResult

The ParserPlugin currently returns a mocked `ParserResult` (DummyParserPlugin).
No Tree-sitter, no real parsing — only the full integration infrastructure.

Design
------
- **ParserManager Integration**: `ParserStage.setup()` seeds `ParserManager` with
  `DummyParserPlugin` instances for each language requested by the job set.
- **Custom Job Handler**: Replaces `JobExecutionEngine`'s default sleep handler with
  `_parser_job_handler()` which routes each job through `ParserManager.execute_parser()`.
- **Result Accumulation**: Collects all `ParserResult` objects into
  `ctx.metadata["parser_results"]` for downstream stage consumption.
- **Error Isolation**: Any plugin crash yields a `ParserStatus.INTERNAL_ERROR` result;
  the engine continues processing remaining jobs.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict, List, Optional, Set

from config.settings import get_settings
from core.execution_context import ExecutionContext
from core.parser_manager import ParserManager
from core.scheduler import Scheduler
from models.parser import ParserLanguage, ParserResult, ParserStatus
from pipeline.stage import PipelineContext, Stage

logger = logging.getLogger(__name__)


def _detect_languages(scheduler: Scheduler) -> Set[ParserLanguage]:
    """
    Inspect queued jobs in the scheduler and enumerate unique requested languages.

    Languages that are not present in the `ParserLanguage` enum are silently mapped to
    `ParserLanguage.UNKNOWN` and skipped to avoid seeding an unusable plugin.
    """
    languages: Set[ParserLanguage] = set()
    for job in scheduler.all_jobs():
        lang_str = (job.language or job.file.language or "").lower().strip()
        try:
            if lang_str:
                languages.add(ParserLanguage(lang_str))
        except ValueError:
            pass
    return languages


def _seed_parser_manager(manager: ParserManager, languages: Set[ParserLanguage]) -> None:
    """
    Register a `DummyParserPlugin` for each language not already in the `ParserManager`.
    """
    from plugins.parser_plugin import DummyParserPlugin

    for lang in languages:
        if lang == ParserLanguage.UNKNOWN:
            continue
        if manager.select_parser(lang) is None:
            plugin = DummyParserPlugin(target_language=lang)
            manager.register_parser(plugin)
            logger.debug(f"[ParserStage] Seeded DummyParserPlugin for '{lang.value}'")


class ParserStage(Stage):
    """
    Pipeline Stage 3 — Parser & ParserManager Integration.

    Execution workflow
    ------------------
    1. ``setup(ctx)``   — Seed `ParserManager` with `DummyParserPlugin` for each language.
    2. ``execute(ctx)`` — Run `JobExecutionEngine` with `_parser_job_handler` routed through
                          `ParserManager → ParserPlugin → ParserResult`.
    3. ``teardown(ctx)``— Shut down all initialized parser plugins; store result counts.
    """

    def __init__(self) -> None:
        self._parser_manager: ParserManager = ParserManager.get_instance()
        self._parser_results: List[ParserResult] = []

    @property
    def name(self) -> str:
        return "Parser"

    def setup(self, ctx: PipelineContext) -> None:
        """Detect languages from queued jobs and seed ParserManager with DummyParserPlugin instances."""
        scheduler: Optional[Scheduler] = ctx.metadata.get("scheduler")
        if scheduler is None:
            logger.debug("[ParserStage] No scheduler found in ctx.metadata — skipping plugin seeding.")
            return

        languages = _detect_languages(scheduler)
        logger.info(
            f"[ParserStage] Detected {len(languages)} language(s) in job queue: "
            f"{[l.value for l in languages]}"
        )
        _seed_parser_manager(self._parser_manager, languages)

    def execute(self, ctx: PipelineContext) -> None:
        """Run all queued AnalysisJobs through ParserManager using the JobExecutionEngine."""
        from core.job_engine import JobExecutionEngine

        scheduler: Optional[Scheduler] = ctx.metadata.get("scheduler")
        settings = get_settings()

        if scheduler is None or scheduler.is_idle():
            logger.info(f"[ParserStage] No scheduled jobs to execute (run_id={ctx.run_id}).")
            ctx.metadata["engine_summary"] = {}
            ctx.metadata["parser_results"] = []
            return

        logger.info(
            f"[ParserStage] Executing {scheduler.pending_count()} job(s) through ParserManager "
            f"(workers={settings.worker_count}, run_id={ctx.run_id})"
        )

        self._parser_results = []

        async def _parser_job_handler(exec_ctx: ExecutionContext) -> None:
            """
            Per-job async handler: routes AnalysisJob through ParserManager → ParserPlugin → ParserResult.
            """
            result = await self._parser_manager.execute_parser(
                job=exec_ctx.job,
                context=exec_ctx,
            )
            self._parser_results.append(result)

            if result.status == ParserStatus.SUCCESS:
                logger.debug(
                    f"[ParserStage] ✓ Parsed '{exec_ctx.job.file.path}' "
                    f"({exec_ctx.job.language}) in {result.statistics.duration_ms:.1f}ms"
                )
            elif result.status == ParserStatus.UNSUPPORTED_LANGUAGE:
                logger.debug(
                    f"[ParserStage] ⚠ Unsupported language for '{exec_ctx.job.file.path}'"
                )
            else:
                logger.warning(
                    f"[ParserStage] ✗ Parse failed for '{exec_ctx.job.file.path}': "
                    f"{result.status.value}"
                )

        engine = JobExecutionEngine(
            scheduler=scheduler,
            pipeline_context=ctx,
            worker_count=settings.worker_count,
            job_timeout_seconds=float(settings.file_timeout_seconds),
            job_handler=_parser_job_handler,
        )

        # Execute async engine
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop and loop.is_running():
            summary = asyncio.run_coroutine_threadsafe(
                engine.run_until_complete(), loop
            ).result()
        else:
            summary = asyncio.run(engine.run_until_complete())

        ctx.metadata["engine_summary"] = summary.to_dict()
        ctx.metadata["parser_results"] = self._parser_results

        success_count = sum(1 for r in self._parser_results if r.status == ParserStatus.SUCCESS)
        fail_count = sum(1 for r in self._parser_results if r.status not in (
            ParserStatus.SUCCESS, ParserStatus.UNSUPPORTED_LANGUAGE
        ))
        unsupported_count = sum(1 for r in self._parser_results if r.status == ParserStatus.UNSUPPORTED_LANGUAGE)

        logger.info(
            f"[ParserStage] Completed: {success_count} parsed, {unsupported_count} unsupported, "
            f"{fail_count} failed — {summary.elapsed_time_seconds:.3f}s "
            f"({summary.throughput_jobs_per_sec:.1f} jobs/s)"
        )

    def teardown(self, ctx: PipelineContext) -> None:
        """Shut down all initialized parser plugins and store final result stats."""
        self._parser_manager.shutdown_all()
        parser_results: List[ParserResult] = ctx.metadata.get("parser_results", [])
        ctx.metadata["parser_stage_stats"] = {
            "total_results": len(parser_results),
            "success": sum(1 for r in parser_results if r.status == ParserStatus.SUCCESS),
            "unsupported": sum(1 for r in parser_results if r.status == ParserStatus.UNSUPPORTED_LANGUAGE),
            "failed": sum(1 for r in parser_results if r.status not in (
                ParserStatus.SUCCESS, ParserStatus.UNSUPPORTED_LANGUAGE
            )),
        }
        logger.debug(f"[ParserStage] teardown complete. Stats: {ctx.metadata['parser_stage_stats']}")
