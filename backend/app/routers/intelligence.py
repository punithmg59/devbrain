import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Repo, User
from app.schemas.intelligence import (
    BottlenecksResponse,
    ChangeRiskReport,
    CriticalComponentsResponse,
    FindingsResponse,
    IntelligenceDashboard,
    RefactorOpportunitiesResponse,
    ArchitectureIntelligenceResponse,
)
from app.services.architecture_intelligence_service import ArchitectureIntelligenceService
from app.utils.auth import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter(tags=["intelligence"])
service = ArchitectureIntelligenceService()


async def _get_user_repo(repo_id: str, current_user: User, db: AsyncSession) -> Repo:
    try:
        rid = UUID(repo_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail="Repository not found") from e
    repo = (
        await db.execute(select(Repo).where(Repo.id == rid, Repo.user_id == current_user.id))
    ).scalar_one_or_none()
    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found")
    return repo


@router.get(
    "/api/repos/{repo_id}/architecture/intelligence/critical",
    response_model=CriticalComponentsResponse,
)
async def get_critical_components(
    repo_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CriticalComponentsResponse:
    repo = await _get_user_repo(repo_id, current_user, db)
    return await service.detect_critical_components(repo.id, db)


@router.get(
    "/api/repos/{repo_id}/architecture/intelligence/bottlenecks",
    response_model=BottlenecksResponse,
)
async def get_bottlenecks(
    repo_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> BottlenecksResponse:
    repo = await _get_user_repo(repo_id, current_user, db)
    return await service.detect_bottlenecks(repo.id, db)


@router.get(
    "/api/repos/{repo_id}/architecture/intelligence/refactor",
    response_model=RefactorOpportunitiesResponse,
)
async def get_refactor_opportunities(
    repo_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> RefactorOpportunitiesResponse:
    repo = await _get_user_repo(repo_id, current_user, db)
    return await service.find_refactor_opportunities(repo.id, db)


@router.get(
    "/api/repos/{repo_id}/architecture/intelligence/risk/{node_id}",
    response_model=ChangeRiskReport,
)
async def get_change_risk(
    repo_id: str,
    node_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ChangeRiskReport:
    repo = await _get_user_repo(repo_id, current_user, db)
    result = await service.predict_change_risk(repo.id, node_id, db)
    if not result:
        raise HTTPException(status_code=404, detail="Node not found")
    return result


@router.get(
    "/api/repos/{repo_id}/architecture/intelligence/findings",
    response_model=FindingsResponse,
)
async def get_findings(
    repo_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> FindingsResponse:
    repo = await _get_user_repo(repo_id, current_user, db)
    return await service.generate_findings(repo.id, db)


@router.get(
    "/api/repos/{repo_id}/architecture/intelligence/dashboard",
    response_model=IntelligenceDashboard,
)
async def get_dashboard(
    repo_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> IntelligenceDashboard:
    repo = await _get_user_repo(repo_id, current_user, db)
    return await service.get_dashboard(repo.id, db)


@router.get(
    "/api/repos/{repo_id}/architecture/intelligence",
    response_model=ArchitectureIntelligenceResponse,
)
async def get_intelligence_agent_response(
    repo_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ArchitectureIntelligenceResponse:
    repo = await _get_user_repo(repo_id, current_user, db)
    dash = await service.get_dashboard(repo.id, db)
    return ArchitectureIntelligenceResponse(
        health_score=dash.architecture_score,
        risk_score=dash.risk_score,
        critical_nodes=dash.critical_components,
        bottlenecks=dash.bottlenecks,
        single_points_of_failure=dash.critical_components,
        refactor_opportunities=dash.refactor_suggestions,
        architecture_findings=dash.top_findings,
    )

