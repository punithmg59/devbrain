"""Flow Reconstruction API.

Exposes architectural flows reconstructed from the existing repository graph by
deterministic BFS / DFS traversal. No AI, no LLM, no new graph structures —
every step is a real edge.
"""

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Repo, User
from app.schemas.flow import (
    FlowDetailResponse,
    FlowListResponse,
    FlowsFromNodeResponse,
    FlowTypeCount,
)
from app.services.flow_reconstruction_service import FlowReconstructionService
from app.utils.auth import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter(tags=["flows"])
service = FlowReconstructionService()


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


@router.get("/api/repos/{repo_id}/flows", response_model=FlowListResponse)
async def list_flows(
    repo_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> FlowListResponse:
    repo = await _get_user_repo(repo_id, current_user, db)
    summaries, type_counts = await service.list_flows(repo.id, db)
    return FlowListResponse(
        repo_id=str(repo.id),
        total=len(summaries),
        type_counts=[
            FlowTypeCount(flow_type=ft, count=c) for ft, c in sorted(type_counts.items())
        ],
        flows=summaries,
    )


@router.get("/api/repos/{repo_id}/flows/from-node/{node_id}", response_model=FlowsFromNodeResponse)
async def flows_from_node(
    repo_id: str,
    node_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> FlowsFromNodeResponse:
    repo = await _get_user_repo(repo_id, current_user, db)
    try:
        nid = str(UUID(node_id))
    except ValueError as e:
        raise HTTPException(status_code=404, detail="Node not found") from e
    node_ref, flows = await service.flows_from_node(repo.id, nid, db)
    if node_ref is None:
        raise HTTPException(status_code=404, detail="Node not found")
    return FlowsFromNodeResponse(
        repo_id=str(repo.id),
        node=node_ref,
        total=len(flows),
        flows=flows,
    )


# NOTE: registered AFTER /from-node so the static segment wins the route match.
@router.get("/api/repos/{repo_id}/flows/{flow_id}", response_model=FlowDetailResponse)
async def get_flow(
    repo_id: str,
    flow_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> FlowDetailResponse:
    repo = await _get_user_repo(repo_id, current_user, db)
    flow = await service.get_flow(repo.id, flow_id, db)
    if flow is None:
        raise HTTPException(status_code=404, detail="Flow not found")
    return FlowDetailResponse(repo_id=str(repo.id), flow=flow)
