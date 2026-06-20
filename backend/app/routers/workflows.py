"""Workflow intelligence API."""

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models import Repo, User
from app.models.workflow import Workflow
from app.schemas.workflow import (
    DiscoverWorkflowsResponse,
    WorkflowApiRef,
    WorkflowDetail,
    WorkflowFeedbackRequest,
    WorkflowFeedbackResponse,
    WorkflowListResponse,
    WorkflowNodeRef,
    WorkflowSummary,
)
from app.services.analysis import ANALYZED_STATUSES
from app.services.workflow_discovery_service import WorkflowDiscoveryService
from app.services.workflow_graph_service import WorkflowGraphService
from app.services.workflow_learning_service import WorkflowLearningService
from app.utils.auth import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter(tags=["workflows"])

discovery = WorkflowDiscoveryService()
graph_service = WorkflowGraphService()
learning = WorkflowLearningService()


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


def _summary(wf: Workflow) -> WorkflowSummary:
    svc = wf.services[0].service_name if wf.services else None
    return WorkflowSummary(
        id=str(wf.id),
        name=wf.name,
        description=wf.description,
        criticality=wf.criticality,
        workflow_type=wf.workflow_type,
        confidence=wf.confidence,
        service_name=svc,
        node_count=len(wf.nodes),
        api_count=len(wf.apis),
    )


@router.post(
    "/api/repos/{repo_id}/workflows/discover",
    response_model=DiscoverWorkflowsResponse,
)
async def discover_workflows(
    repo_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DiscoverWorkflowsResponse:
    repo = await _get_user_repo(repo_id, current_user, db)
    if repo.analysis_status not in ANALYZED_STATUSES:
        raise HTTPException(status_code=400, detail="Repository analysis not complete")
    count = await discovery.discover_for_repo(repo.id, db)
    workflows = await discovery.list_workflows(repo.id, db)
    return DiscoverWorkflowsResponse(
        discovered=count,
        workflows=[_summary(w) for w in workflows],
        message=f"Discovered {count} workflows from repository graph evidence.",
    )


@router.post(
    "/api/repos/{repo_id}/workflows/rebuild",
    response_model=DiscoverWorkflowsResponse,
)
async def rebuild_workflows(
    repo_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DiscoverWorkflowsResponse:
    return await discover_workflows(repo_id, current_user, db)


@router.get(
    "/api/repos/{repo_id}/workflows",
    response_model=WorkflowListResponse,
)
async def list_workflows(
    repo_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> WorkflowListResponse:
    repo = await _get_user_repo(repo_id, current_user, db)
    workflows = await discovery.list_workflows(repo.id, db)
    return WorkflowListResponse(
        workflows=[_summary(w) for w in workflows],
        total=len(workflows),
    )


@router.get(
    "/api/repos/{repo_id}/workflows/{workflow_id}",
    response_model=WorkflowDetail,
)
async def get_workflow_detail(
    repo_id: str,
    workflow_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> WorkflowDetail:
    repo = await _get_user_repo(repo_id, current_user, db)
    try:
        wf_uuid = UUID(workflow_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail="Invalid workflow id") from e

    wf = await discovery.get_workflow(repo.id, wf_uuid, db)
    if not wf:
        raise HTTPException(status_code=404, detail="Workflow not found")

    from app.services.journey_service import journey_names_for_workflows

    node_rows = (
        await db.execute(
            select(Workflow)
            .where(Workflow.id == wf.id)
            .options(selectinload(Workflow.nodes))
        )
    )
    wf_loaded = node_rows.scalar_one()

    from sqlalchemy import text

    nodes_detail = (
        await db.execute(
            text("""
                SELECT n.id, n.name, n.node_type,
                       COALESCE(rf.file_path, n.full_path) AS file_path,
                       wn.relationship_type
                FROM workflow_nodes wn
                JOIN nodes n ON n.id = wn.node_id
                LEFT JOIN repo_files rf ON n.file_id = rf.id
                WHERE wn.workflow_id = :wf_id
                ORDER BY n.name
            """),
            {"wf_id": str(wf.id)},
        )
    ).mappings()

    file_paths = (
        await db.execute(
            text("""
                SELECT rf.file_path FROM workflow_files wf
                JOIN repo_files rf ON rf.id = wf.file_id
                WHERE wf.workflow_id = :wf_id
            """),
            {"wf_id": str(wf.id)},
        )
    ).scalars().all()

    related = await graph_service.related_workflow_names(wf, repo.id, db)
    journeys = journey_names_for_workflows({wf.name})

    return WorkflowDetail(
        id=str(wf.id),
        name=wf.name,
        description=wf.description,
        criticality=wf.criticality,
        workflow_type=wf.workflow_type,
        confidence=wf.confidence,
        service_name=wf.services[0].service_name if wf.services else None,
        node_count=len(wf_loaded.nodes),
        api_count=len(wf.apis),
        reasoning=wf.reasoning,
        source_evidence=wf.source_evidence,
        nodes=[
            WorkflowNodeRef(
                node_id=str(r["id"]),
                name=r["name"],
                node_type=r["node_type"],
                file_path=r["file_path"] or "",
                relationship_type=r["relationship_type"],
            )
            for r in nodes_detail
        ],
        apis=[
            WorkflowApiRef(api_route=a.api_route) for a in wf.apis
        ],
        services=[s.service_name for s in wf.services],
        files=list(file_paths),
        related_workflows=related,
        user_journeys=journeys,
        created_at=wf.created_at,
        updated_at=wf.updated_at,
    )


@router.post(
    "/api/repos/{repo_id}/workflows/feedback",
    response_model=WorkflowFeedbackResponse,
)
async def workflow_feedback(
    repo_id: str,
    body: WorkflowFeedbackRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> WorkflowFeedbackResponse:
    repo = await _get_user_repo(repo_id, current_user, db)
    try:
        wf_uuid = UUID(body.workflow_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail="Invalid workflow id") from e

    if body.accepted == body.rejected:
        raise HTTPException(
            status_code=400,
            detail="Specify exactly one of accepted or rejected",
        )

    confidence, message = await learning.record_feedback(
        repo.id,
        body.query.strip(),
        wf_uuid,
        accepted=body.accepted,
        rejected=body.rejected,
        db=db,
    )
    if confidence is None:
        raise HTTPException(status_code=404, detail=message)

    return WorkflowFeedbackResponse(
        ok=True,
        workflow_id=body.workflow_id,
        new_confidence=confidence,
        message=message,
    )
