"""pipeline/scheduler.py – Stage 2: work scheduling.

Reads ``discovered_files`` from the pipeline context, wraps each
``RepositoryFile`` in an ``AnalysisJob``, builds a priority queue via the
``Scheduler`` service, and stores it in ``ctx.metadata`` for downstream stages.
"""
from __future__ import annotations

import logging
from typing import List

from core.scheduler import Scheduler
from models.job import AnalysisJob, JobPriority
from models.repository import Language, RepositoryFile
from pipeline.stage import PipelineContext, Stage

logger = logging.getLogger(__name__)


# Priority overrides applied before queuing.
# Entry-point / config files warrant a higher dispatch priority.
_HIGH_PRIORITY_EXTENSIONS = frozenset({"py", "ts", "js", "go", "java", "cs"})
_CRITICAL_FILENAMES = frozenset({
    "main.py", "app.py", "index.ts", "index.js", "main.go",
    "Program.cs", "Main.java", "manage.py",
})


def _priority_for(file: RepositoryFile) -> JobPriority:
    """Assign scheduling priority based on file name and extension."""
    if file.name in _CRITICAL_FILENAMES:
        return JobPriority.CRITICAL
    if file.extension in _HIGH_PRIORITY_EXTENSIONS:
        return JobPriority.HIGH
    if file.language == Language.UNKNOWN.value:
        return JobPriority.LOW
    return JobPriority.NORMAL


class SchedulerStage(Stage):
    """
    Pipeline Stage 2 — Work Scheduling.

    Converts each ``RepositoryFile`` discovered in Stage 1 into an
    ``AnalysisJob``, enqueues all jobs into a ``Scheduler`` priority queue,
    and exposes the scheduler instance through ``ctx.metadata["scheduler"]``
    for the Parser stage (Phase 2.3+) to consume.

    Design decisions
    ~~~~~~~~~~~~~~~~
    - Uses ``submit_many()`` for a single lock acquisition over the whole batch,
      making scheduling O(n log n) with minimal lock contention.
    - Priority assignment is a pure function of file metadata — no I/O.
    - Unknown-language files are given LOW priority (not skipped) so plugins
      can still choose to handle them.
    - The ``Scheduler`` instance is placed in ``ctx.metadata`` rather than
      instantiated as a singleton so each pipeline run gets an isolated queue.
    """

    @property
    def name(self) -> str:
        return "Scheduler"

    def setup(self, ctx: PipelineContext) -> None:
        logger.debug("[Scheduler] setup – initialising work queue")

    def execute(self, ctx: PipelineContext) -> None:
        discovered_files: List[RepositoryFile] = ctx.metadata.get("discovered_files", [])
        repository_id: str = ctx.repository_id

        scheduler = Scheduler()

        jobs: List[AnalysisJob] = [
            AnalysisJob.from_repository_file(
                repository_id=repository_id,
                file=f,
                priority=_priority_for(f),
            )
            for f in discovered_files
        ]

        if jobs:
            scheduler.submit_many(jobs)

        ctx.metadata["scheduler"] = scheduler
        ctx.metadata["scheduled_batches"] = []  # reserved for future batching

        stats = scheduler.statistics()
        progress = scheduler.progress()

        logger.info(
            f"[Scheduler] Scheduled {stats.total_submitted} job(s) for analysis "
            f"(run_id={ctx.run_id}, queued={progress.queued}, "
            f"languages={list(stats.language_distribution.keys())})"
        )

    def teardown(self, ctx: PipelineContext) -> None:
        logger.debug("[Scheduler] teardown – releasing work queue")
