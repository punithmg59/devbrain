"""
Natural Language Question Router

Provides API endpoints for processing natural language engineering questions.
"""

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Repo, User
from app.schemas.nlq import NLQRequest, NLQResponse
from app.schemas.engineering_intelligence import EngineeringIntelligenceResponse
from app.services.nlq_engine import NLQEngine
from app.utils.auth import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter(tags=["nlq"])


async def _get_user_repo(repo_id: str, current_user: User, db: AsyncSession) -> Repo:
    """Get and validate user repository."""
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


@router.post("/api/repos/{repo_id}/nlq/query", response_model=EngineeringIntelligenceResponse)
async def process_nlq(
    repo_id: str,
    request: NLQRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Process a natural language engineering question with comprehensive Engineering Intelligence.

    All AI pipeline failures are returned as structured error responses.
    Raw Python tracebacks are never exposed — full details are written to
    the backend log with the correlation_id for tracing.

    Supported question types:
    - Delete: "What breaks if I delete AuthService?"
    - Rename: "Rename UserService to CustomerService"
    - Move: "Move AuthService to the auth module"
    - Modify: "Modify the PaymentService"
    - Dependency Query: "What does AuthService depend on?"
    - Repository Query: "What services are in the repository?"
    - Architecture Guidance: "How should I structure the payment module?"
    - Feature Planning: "How do I implement a new notification system?"
    - Refactoring Guidance: "How should I refactor the OrderService?"
    """
    repo = await _get_user_repo(repo_id, current_user, db)

    correlation_id = None
    try:
        nlq_engine = NLQEngine(db=db)
        result = await nlq_engine.process_question(
            repo_id=str(repo.id),
            question=request.question,
            db=db,
        )

        # Pipeline returned a structured error — do NOT raise; return clean JSON
        if isinstance(result, dict) and result.get("success") is False:
            correlation_id = result.get("correlation_id", "unknown")
            stage = result.get("stage", "unknown")
            recoverable = result.get("recoverable", True)
            logger.error(
                f"[{correlation_id}] Pipeline stage '{stage}' failed. "
                f"recoverable={recoverable}"
            )
            status = 422 if recoverable else 500
            return JSONResponse(status_code=status, content=result)

        return EngineeringIntelligenceResponse(**result)

    except HTTPException:
        # Re-raise FastAPI exceptions unchanged (e.g. 404 from _get_user_repo)
        raise

    except Exception as exc:
        # Last-resort safety net — log traceback, never expose it
        import traceback as _tb
        import uuid as _uuid
        cid = correlation_id or str(_uuid.uuid4())
        logger.error(
            f"[{cid}] Unhandled exception in NLQ router for repo={repo_id}: "
            f"{type(exc).__name__}: {exc}\n{_tb.format_exc()}"
        )
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "stage": "router",
                "error_type": type(exc).__name__,
                "message": "An internal error occurred. Please try again or contact support.",
                "correlation_id": cid,
                "recoverable": False,
            },
        )
