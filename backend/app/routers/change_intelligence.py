from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.repo import Repo
from app.models.user import User
from app.services.change_intelligence.schemas import ChangeIntelligenceRequest, ChangeIntelligenceResponse
from app.services.change_intelligence.service import ChangeIntelligenceService
from app.utils.auth import get_current_user
from app.utils.errors import DevBrainException

router = APIRouter(tags=["change-intelligence"])


async def _get_user_repo(repo_id: str, current_user: User, db: AsyncSession) -> Repo:
    try:
        rid = UUID(repo_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid repository id") from exc

    repo = await db.get(Repo, rid)
    if repo is None:
        raise HTTPException(status_code=404, detail="Repository not found")
    if repo.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Repository access denied")
    return repo


@router.post("/api/repos/{repo_id}/change-intelligence", response_model=ChangeIntelligenceResponse)
async def analyze_change_intelligence(
    repo_id: str,
    payload: ChangeIntelligenceRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ChangeIntelligenceResponse:
    repo = await _get_user_repo(repo_id, current_user, db)
    service = ChangeIntelligenceService()
    try:
        return await service.analyze_change(repo, payload, db)
    except DevBrainException as exc:
        raise HTTPException(status_code=exc.status_code, detail={"code": exc.code, "message": exc.message}) from exc
