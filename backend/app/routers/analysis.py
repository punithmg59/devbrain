import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Repo, User, AnalysisJob
from app.schemas.analysis import AnalysisStatusResponse, AnalysisTriggerResponse
from app.schemas.repo import RepoResponse
from app.utils.auth import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter(tags=["analysis"])


async def _get_user_repo(
    repo_id: str,
    current_user: User,
    db: AsyncSession,
) -> Repo:
    try:
        uid = UUID(repo_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail="Invalid repository id") from e

    result = await db.execute(
        select(Repo).where(Repo.id == uid, Repo.user_id == current_user.id)
    )
    repo = result.scalar_one_or_none()
    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found")
    return repo


from datetime import datetime, timezone

@router.post("/api/repos/{repo_id}/analyze", response_model=AnalysisTriggerResponse)
async def trigger_analysis(
    repo_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AnalysisTriggerResponse:
    repo = await _get_user_repo(repo_id, current_user, db)

    # Check for an already-active job
    existing_job = (await db.execute(
        select(AnalysisJob)
        .where(AnalysisJob.repo_id == repo.id)
        .where(AnalysisJob.status.notin_(["completed", "completed_with_warnings", "failed"]))
        .order_by(AnalysisJob.created_at.desc())
        .limit(1)
    )).scalar_one_or_none()

    if existing_job:
        from app.services.analysis import is_analysis_running
        now_utc = datetime.now(timezone.utc)
        hb = existing_job.heartbeat_at or existing_job.created_at
        if hb and hb.tzinfo is None:
            hb = hb.replace(tzinfo=timezone.utc)
        is_stale = hb is None or (now_utc - hb).total_seconds() > 90

        if not is_analysis_running(repo.id) and is_stale:
            logger.warning("Marking stale job %s as failed to allow re-analysis for repo %s", existing_job.id, repo.id)
            existing_job.status = "failed"
            existing_job.error_message = "Superceded by manual re-analysis request"
            await db.flush()
        else:
            return AnalysisTriggerResponse(
                repo_id=str(repo.id),
                status=existing_job.status,
                message="Analysis already in progress",
                job_id=str(existing_job.id),
            )

    # Create a new AnalysisJob row
    job = AnalysisJob(
        repo_id=repo.id,
        user_id=current_user.id,
        status="queued",
    )
    db.add(job)
    repo.analysis_status = "queued"
    await db.commit()

    logger.info("Queued analysis job %s for %s", job.id, repo.full_name)
    logger.info(
        "[ANALYSIS] job_created job_id=%s repo_id=%s status=queued user_id=%s",
        job.id, repo.id, current_user.id,
    )

    return AnalysisTriggerResponse(
        repo_id=str(repo.id),
        status="queued",
        message="Analysis queued successfully",
        job_id=str(job.id),
    )


@router.get("/api/repos/{repo_id}/analysis", response_model=AnalysisStatusResponse)
async def get_analysis_status(
    repo_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AnalysisStatusResponse:
    repo = await _get_user_repo(repo_id, current_user, db)
    return AnalysisStatusResponse(
        repo_id=str(repo.id),
        full_name=repo.full_name,
        analysis_status=repo.analysis_status,
        total_files=repo.total_files,
        total_functions=repo.total_functions,
        total_lines=repo.total_lines,
        last_analyzed_at=repo.last_analyzed_at,
    )


@router.get("/api/repos/{repo_id}/analysis-progress")
async def get_analysis_progress(
    repo_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    repo = await _get_user_repo(repo_id, current_user, db)

    # Get the most recent job for this repo
    job = (await db.execute(
        select(AnalysisJob)
        .where(AnalysisJob.repo_id == repo.id)
        .order_by(AnalysisJob.created_at.desc())
        .limit(1)
    )).scalar_one_or_none()

    if not job:
        # No job yet — repo may have been analyzed before the queue existed
        return {
            "status": repo.analysis_status or "unknown",
            "current_stage": repo.analysis_status or "unknown",
            "progress_percent": 100.0 if repo.analysis_status == "completed" else 0.0,
            "files_processed": 0,
            "files_total": getattr(repo, "total_files", 0) or 0,
            "functions_found": getattr(repo, "total_functions", 0) or 0,
            "nodes_count": 0,
            "edges_count": 0,
            "files_failed": 0,
            "warnings": [],
            "duration_seconds": None,
            "job_id": None,
        }

    return {
        "status": job.status,
        "current_stage": job.current_stage,
        "progress_percent": round(job.progress_percent, 1),
        "files_processed": job.files_processed,
        "files_total": job.files_total,
        "functions_found": job.functions_found,
        "nodes_count": job.nodes_count,
        "edges_count": job.edges_count,
        "files_failed": job.files_failed,
        "warnings": job.warnings or [],
        "duration_seconds": job.duration_seconds,
        "job_id": str(job.id),
    }


@router.get("/api/repos/{repo_id}", response_model=RepoResponse)
async def get_repo(
    repo_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Repo:
    return await _get_user_repo(repo_id, current_user, db)
