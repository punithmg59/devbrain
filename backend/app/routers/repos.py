import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Repo, User
from app.schemas.repo import ConnectRepoRequest, GitHubRepoItem, RepoResponse
from app.services.analysis import is_stale_in_progress, recover_stale_analysis
from app.utils.auth import get_current_user
from app.utils.github import fetch_github_repos, get_github_token

logger = logging.getLogger(__name__)
router = APIRouter(tags=["repos"])


@router.get("/api/repos", response_model=list[RepoResponse])
async def list_connected_repos(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[Repo]:
    result = await db.execute(
        select(Repo)
        .where(Repo.user_id == current_user.id)
        .order_by(Repo.updated_at.desc())
    )
    repos = list(result.scalars().all())
    for repo in repos:
        if is_stale_in_progress(repo):
            await recover_stale_analysis(db, repo)
    return repos


@router.get("/api/repos/github/available", response_model=list[GitHubRepoItem])
async def list_available_github_repos(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[GitHubRepoItem]:
    token = await get_github_token(current_user, db)
    github_repos = await fetch_github_repos(token)

    connected_result = await db.execute(
        select(Repo.github_repo_id).where(Repo.user_id == current_user.id)
    )
    connected_ids = set(connected_result.scalars().all())

    return [
        GitHubRepoItem(
            github_repo_id=repo["id"],
            full_name=repo["full_name"],
            name=repo["name"],
            description=repo.get("description"),
            default_branch=repo.get("default_branch") or "main",
            is_private=repo.get("private", False),
            language=repo.get("language"),
            already_connected=repo["id"] in connected_ids,
        )
        for repo in github_repos
    ]


@router.post("/api/repos/connect", response_model=RepoResponse)
async def connect_repo(
    body: ConnectRepoRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Repo:
    existing = await db.execute(select(Repo).where(Repo.github_repo_id == body.github_repo_id))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Repository already connected")

    token = await get_github_token(current_user, db)
    github_repos = await fetch_github_repos(token)
    github_repo = next((r for r in github_repos if r["id"] == body.github_repo_id), None)
    if github_repo is None:
        raise HTTPException(status_code=404, detail="Repository not found on GitHub")

    repo = Repo(
        user_id=current_user.id,
        github_repo_id=github_repo["id"],
        full_name=github_repo["full_name"],
        name=github_repo["name"],
        description=github_repo.get("description"),
        default_branch=github_repo.get("default_branch") or "main",
        is_private=github_repo.get("private", False),
        language=github_repo.get("language"),
        analysis_status="pending",
    )
    db.add(repo)
    await db.flush()
    await db.refresh(repo)
    logger.info("Connected repo %s for user %s", repo.full_name, current_user.username)
    return repo


@router.delete("/api/repos/{repo_id}")
async def disconnect_repo(
    repo_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    result = await db.execute(
        select(Repo).where(Repo.id == UUID(repo_id), Repo.user_id == current_user.id)
    )
    repo = result.scalar_one_or_none()
    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found")
    await db.delete(repo)
    return {"message": "Repository disconnected"}
