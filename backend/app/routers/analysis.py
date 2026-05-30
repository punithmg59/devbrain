import logging
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Repo, User
from app.schemas.analysis import AnalysisStatusResponse, AnalysisTriggerResponse
from app.schemas.repo import RepoResponse
from app.services.analysis import (
    is_analysis_running,
    is_stale_in_progress,
    recover_stale_analysis,
    run_repo_analysis,
)
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


@router.post("/api/repos/{repo_id}/analyze", response_model=AnalysisTriggerResponse)
async def trigger_analysis(
    repo_id: str,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AnalysisTriggerResponse:
    repo = await _get_user_repo(repo_id, current_user, db)

    if is_stale_in_progress(repo):
        await recover_stale_analysis(db, repo)

    if repo.analysis_status in ("analyzing", "queued") and is_analysis_running(repo.id):
        return AnalysisTriggerResponse(
            repo_id=str(repo.id),
            status=repo.analysis_status,
            message="Analysis is already in progress",
        )

    if repo.analysis_status in ("analyzing", "queued") and not is_analysis_running(repo.id):
        await recover_stale_analysis(db, repo)

    repo.analysis_status = "queued"
    await db.flush()

    background_tasks.add_task(run_repo_analysis, repo.id, current_user.id)
    logger.info("Queued analysis for %s", repo.full_name)

    return AnalysisTriggerResponse(
        repo_id=str(repo.id),
        status="queued",
        message="Repository analysis started",
    )


@router.get("/api/repos/{repo_id}/analysis", response_model=AnalysisStatusResponse)
async def get_analysis_status(
    repo_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AnalysisStatusResponse:
    repo = await _get_user_repo(repo_id, current_user, db)
    if is_stale_in_progress(repo):
        await recover_stale_analysis(db, repo)
    return AnalysisStatusResponse(
        repo_id=str(repo.id),
        full_name=repo.full_name,
        analysis_status=repo.analysis_status,
        total_files=repo.total_files,
        total_functions=repo.total_functions,
        total_lines=repo.total_lines,
        last_analyzed_at=repo.last_analyzed_at,
    )


@router.get("/api/repos/{repo_id}", response_model=RepoResponse)
async def get_repo(
    repo_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Repo:
    return await _get_user_repo(repo_id, current_user, db)
