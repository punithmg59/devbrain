import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Repo, User
from app.schemas.architecture import (
    ArchitectureComponents,
    ArchitectureDependencies,
    ArchitectureExplanation,
    ArchitectureOverview,
    NodeDetails,
    ArchitectureHealthReport,
    ArchitectureStory,
)
from app.services.architecture_explainer_service import ArchitectureExplainerService
from app.services.architecture_service import ArchitectureService
from app.utils.auth import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter(tags=["architecture"])
service = ArchitectureService()
explainer = ArchitectureExplainerService()


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
    "/api/repos/{repo_id}/architecture/overview",
    response_model=ArchitectureOverview,
)
async def architecture_overview(
    repo_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ArchitectureOverview:
    repo = await _get_user_repo(repo_id, current_user, db)
    # Not gated on analysis status: an un-analyzed repo simply returns zeros.
    return await service.get_overview(repo.id, db)


@router.get(
    "/api/repos/{repo_id}/architecture/components",
    response_model=ArchitectureComponents,
)
async def architecture_components(
    repo_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ArchitectureComponents:
    repo = await _get_user_repo(repo_id, current_user, db)
    return await service.get_components(repo.id, db)


@router.get(
    "/api/repos/{repo_id}/architecture/node/{node_id}",
    response_model=NodeDetails,
)
async def architecture_node(
    repo_id: str,
    node_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> NodeDetails:
    repo = await _get_user_repo(repo_id, current_user, db)
    try:
        nid = UUID(node_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail="Node not found") from e
    details = await service.get_node_details(repo.id, nid, db)
    if details is None:
        raise HTTPException(status_code=404, detail="Node not found")
    return details


@router.get(
    "/api/repos/{repo_id}/architecture/dependencies",
    response_model=ArchitectureDependencies,
)
async def architecture_dependencies(
    repo_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ArchitectureDependencies:
    repo = await _get_user_repo(repo_id, current_user, db)
    return await service.get_dependencies(repo.id, db)


@router.get(
    "/api/repos/{repo_id}/architecture/explain/{node_id}",
    response_model=ArchitectureExplanation,
)
async def architecture_explain_node(
    repo_id: str,
    node_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ArchitectureExplanation:
    """Natural-language architecture explanation of a node, grounded in graph
    evidence (callers / callees / services / tables / dependencies). Groq writes
    the prose; the graph is the source of truth and nothing is invented."""
    repo = await _get_user_repo(repo_id, current_user, db)
    try:
        nid = UUID(node_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail="Node not found") from e
    explanation = await explainer.explain_node(repo.id, nid, db)
    if explanation is None:
        raise HTTPException(status_code=404, detail="Node not found")
    return explanation


@router.get(
    "/api/repos/{repo_id}/architecture/explain-flow/{flow_id}",
    response_model=ArchitectureExplanation,
)
async def architecture_explain_flow(
    repo_id: str,
    flow_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ArchitectureExplanation:
    """Natural-language explanation of a reconstructed flow. The flow is rebuilt
    deterministically by the Flow Reconstruction Engine; Groq narrates only the
    graph evidence it produces."""
    repo = await _get_user_repo(repo_id, current_user, db)
    explanation = await explainer.explain_flow(repo.id, flow_id, db)
    if explanation is None:
        raise HTTPException(status_code=404, detail="Flow not found")
    return explanation


@router.get(
    "/api/repos/{repo_id}/architecture/health",
    response_model=ArchitectureHealthReport,
)
async def architecture_health(
    repo_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ArchitectureHealthReport:
    """Deterministic, graph-driven evaluation of architecture quality."""
    from app.services.architecture_health import ArchitectureHealthService
    repo = await _get_user_repo(repo_id, current_user, db)
    return await ArchitectureHealthService.evaluate_health(repo.id, db)


@router.get(
    "/api/repos/{repo_id}/architecture/story",
    response_model=ArchitectureStory,
)
async def architecture_story(
    repo_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ArchitectureStory:
    """Guided narrative story of the architecture, powered by deterministic metrics."""
    from app.services.architecture_story_service import ArchitectureStoryService
    repo = await _get_user_repo(repo_id, current_user, db)
    return await ArchitectureStoryService.generate_story(repo.id, db)


@router.get(
    "/api/repos/{repo_id}/architecture/story/overview",
    response_model=ArchitectureStory,
)
async def architecture_story_overview(
    repo_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ArchitectureStory:
    """Guided narrative story overview."""
    from app.services.architecture_story_service import ArchitectureStoryService
    repo = await _get_user_repo(repo_id, current_user, db)
    return await ArchitectureStoryService.generate_story(repo.id, db)
