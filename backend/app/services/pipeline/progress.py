import logging
from datetime import datetime, timezone
from typing import Callable

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.analysis_job import AnalysisJob, FileError
from app.models.repo import Repo

logger = logging.getLogger(__name__)

# Maps stage name to the progress floor percentage shown to the user.
# Within the parsing stage, percentage interpolates from 15 to 70
# based on files_processed / files_total.
STAGE_FLOOR: dict[str, float] = {
    "queued":                  0.0,
    "cloning":                 2.0,
    "scanning":                8.0,
    "parsing":                15.0,
    "building_graph":         70.0,
    "saving":                 88.0,
    "completed":             100.0,
    "completed_with_warnings": 100.0,
    "failed":                100.0,
}


class ProgressReporter:
    """
    Writes stage transitions, progress percentages, file counts,
    and final metrics to the AnalysisJob row in the database.

    All methods are async and commit immediately so the frontend
    polling /analysis-progress always sees fresh data.
    """

    def __init__(self, db: AsyncSession, job: AnalysisJob, repo: Repo):
        self.db = db
        self.job = job
        self.repo = repo

    async def set_stage(self, stage: str) -> None:
        """
        Transition to a new pipeline stage.
        Updates job.status, job.current_stage, job.progress_percent,
        job.heartbeat_at, and repo.analysis_status.
        Commits immediately.
        """
        floor = STAGE_FLOOR.get(stage, 0.0)
        self.job.status = stage
        self.job.current_stage = stage
        self.job.progress_percent = floor
        self.job.heartbeat_at = datetime.now(timezone.utc)
        self.repo.analysis_status = stage
        await self.db.commit()
        logger.info("Job %s → stage: %s (%.0f%%)", self.job.id, stage, floor)

    async def set_files_total(self, total: int) -> None:
        """Call after scanning to set the total file count."""
        self.job.files_total = total
        await self.db.commit()

    def make_parsing_progress_callback(self) -> Callable[[int], None]:
        """
        Returns a synchronous callback compatible with parse_all(on_progress=...).
        The callback updates in-memory fields only — it does NOT await.
        The orchestrator commits periodically via heartbeat_tick().

        Progress interpolates from 15% (parsing start) to 70% (building_graph)
        based on files_processed / files_total.
        """
        job = self.job

        def callback(done: int) -> None:
            job.files_processed = done
            if job.files_total and job.files_total > 0:
                span = STAGE_FLOOR["building_graph"] - STAGE_FLOOR["parsing"]
                pct = STAGE_FLOOR["parsing"] + span * (done / job.files_total)
                job.progress_percent = round(min(pct, 69.9), 1)

        return callback

    async def commit_parsing_progress(self) -> None:
        """
        Persist the in-memory progress updates from the parsing callback.
        Call this from the orchestrator after parse_all() returns.
        """
        self.job.heartbeat_at = datetime.now(timezone.utc)
        await self.db.commit()

    async def set_graph_counts(
        self,
        *,
        nodes: int,
        edges: int,
        functions: int,
        files: int,
    ) -> None:
        """Call after graph building stage with final counts."""
        self.job.nodes_count = nodes
        self.job.edges_count = edges
        self.job.functions_found = functions
        self.job.files_total = files
        await self.db.commit()

    async def record_file_errors(self, errors: list[dict]) -> None:
        """
        Persist file-level parse errors as FileError rows.
        Also updates job.files_failed and job.warnings (capped at 200).
        errors: list of dicts with keys file_path, error_type, message.
        """
        self.job.files_failed = len(errors)
        self.job.warnings = errors[:200]
        for err in errors:
            self.db.add(FileError(
                job_id=self.job.id,
                repo_id=self.repo.id,
                file_path=err.get("file_path", "unknown"),
                error_type=err.get("error_type", "UnknownError"),
                message=err.get("message", "")[:2000],
            ))
        await self.db.commit()

    async def finish(self, final_status: str, elapsed_seconds: float) -> None:
        """
        Mark job as terminal. Compute and store performance metrics.
        final_status must be one of: completed, completed_with_warnings, failed
        """
        self.job.status = final_status
        self.job.current_stage = final_status
        self.job.progress_percent = 100.0
        self.job.finished_at = datetime.now(timezone.utc)
        self.job.duration_seconds = elapsed_seconds

        if elapsed_seconds > 0:
            self.job.files_per_second = round(
                (self.job.files_processed or 0) / elapsed_seconds, 2
            )
            self.job.nodes_per_second = round(
                (self.job.nodes_count or 0) / elapsed_seconds, 2
            )
            self.job.edges_per_second = round(
                (self.job.edges_count or 0) / elapsed_seconds, 2
            )

        self.repo.analysis_status = final_status
        self.repo.last_analyzed_at = datetime.now(timezone.utc)
        await self.db.commit()
        logger.info(
            "Job %s finished: %s in %.1fs (%d files, %d nodes, %d edges)",
            self.job.id, final_status, elapsed_seconds,
            self.job.files_processed, self.job.nodes_count, self.job.edges_count,
        )

    async def fail(self, message: str) -> None:
        """
        Mark job as failed with an error message.
        Safe to call from inside an except block.
        """
        try:
            self.job.status = "failed"
            self.job.current_stage = "failed"
            self.job.progress_percent = 100.0
            self.job.error_message = message[:1000]
            self.job.finished_at = datetime.now(timezone.utc)
            self.repo.analysis_status = "failed"
            self.repo.failure_reason = message[:1000]
            await self.db.commit()
            logger.error("Job %s failed: %s", self.job.id, message)
        except Exception as commit_err:
            logger.error(
                "Could not persist failure for job %s: %s", self.job.id, commit_err
            )
