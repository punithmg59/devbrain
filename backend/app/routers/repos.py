import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Repo, User
from app.schemas.repo import ConnectRepoRequest, GitHubRepoItem, RepoResponse
from app.services.analysis import is_stale_in_progress, recover_stale_analysis
from app.utils.auth import get_current_user
from app.utils.github import fetch_github_repos, get_github_token

logger = logging.getLogger(__name__)
router = APIRouter(tags=["repos"])

# SQL for upstream traversal (callers)
UPSTREAM_CALLERS_SQL = text("""
WITH RECURSIVE upstream AS (
    SELECT n.id, n.name, n.node_type,
           COALESCE(rf.file_path, '') as file_path,
           n.start_line, n.end_line, 0 as depth,
           ARRAY[n.id::text] as visited
    FROM nodes n
    LEFT JOIN repo_files rf ON n.file_id = rf.id
    WHERE n.id = :node_id AND n.repo_id = :repo_id
    UNION ALL
    SELECT n2.id, n2.name, n2.node_type,
           COALESCE(rf2.file_path, '') as file_path,
           n2.start_line, n2.end_line, us.depth + 1,
           us.visited || n2.id::text
    FROM upstream us
    JOIN edges e ON e.to_node_id = us.id
    JOIN nodes n2 ON n2.id = e.from_node_id
    LEFT JOIN repo_files rf2 ON n2.file_id = rf2.id
    WHERE us.depth < :max_depth
      AND NOT n2.id::text = ANY(us.visited)
      AND n2.repo_id = :repo_id
)
SELECT DISTINCT ON (id) id, name, node_type, file_path,
       start_line, end_line, depth
FROM upstream WHERE depth > 0 ORDER BY id, depth
""")


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
    from app.services.repo_deletion import RepositoryDeletionService
    await RepositoryDeletionService.delete_repository(db, UUID(repo_id), current_user.id)
    return {"message": "Repository deleted successfully"}


@router.get("/api/repos/{repo_id}/callers/{node_id}")
async def get_node_callers(
    repo_id: str,
    node_id: str,
    max_depth: int = 5,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Get all callers (incoming edges) for a specific node in the repository graph."""
    # Verify user has access to this repo
    repo_result = await db.execute(
        select(Repo).where(Repo.id == UUID(repo_id), Repo.user_id == current_user.id)
    )
    repo = repo_result.scalar_one_or_none()
    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found")

    # Get target node info
    target_result = await db.execute(
        text("""
            SELECT id, name, node_type
            FROM nodes
            WHERE id = :node_id AND repo_id = :repo_id
        """),
        {"node_id": node_id, "repo_id": repo_id}
    )
    target = target_result.mappings().first()
    if not target:
        raise HTTPException(status_code=404, detail="Node not found")

    # Traverse upstream to get callers
    callers_result = await db.execute(
        UPSTREAM_CALLERS_SQL,
        {"node_id": node_id, "repo_id": repo_id, "max_depth": max_depth}
    )
    callers = [dict(row._mapping) for row in callers_result.mappings()]

    # Convert UUID to string
    for caller in callers:
        if isinstance(caller["id"], UUID):
            caller["id"] = str(caller["id"])

    # Group by type
    type_counts = {
        "api_route": 0,
        "service": 0,
        "class": 0,
        "function": 0,
        "method": 0,
        "workflow": 0,
        "other": 0
    }

    for caller in callers:
        node_type = caller.get("node_type", "other").lower()
        if node_type in type_counts:
            type_counts[node_type] += 1
        else:
            type_counts["other"] += 1

    # Determine critical callers (depth 1 or high centrality nodes)
    critical_callers = [c for c in callers if c.get("depth", 0) == 1]

    # Sort callers: critical first, then by depth, then alphabetically
    callers.sort(key=lambda x: (
        0 if x.get("depth", 0) == 1 else 1,  # Critical (depth 1) first
        x.get("depth", 0),  # Then by depth
        x.get("name", "").lower()  # Then alphabetically
    ))

    return {
        "target": {
            "id": str(target["id"]),
            "name": target["name"],
            "type": target["node_type"]
        },
        "summary": {
            "total_callers": len(callers),
            "critical_callers": len(critical_callers),
            "api_routes": type_counts["api_route"],
            "services": type_counts["service"],
            "classes": type_counts["class"],
            "functions": type_counts["function"] + type_counts["method"],
            "workflows": type_counts["workflow"]
        },
        "callers": [
            {
                "id": c["id"],
                "name": c["name"],
                "type": c["node_type"],
                "file": c.get("file_path", ""),
                "depth": c.get("depth", 0),
                "critical": c.get("depth", 0) == 1,
                "start_line": c.get("start_line"),
                "end_line": c.get("end_line")
            }
            for c in callers
        ]
    }


@router.post("/api/repos/{repo_id}/simulate")
async def simulate_change(
    repo_id: str,
    body: dict,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Simulate the effects of a software change using graph traversal."""
    from app.services.simulation_engine import ChangeSimulationEngine
    from app.services.entity_resolution.entity_resolver import EntityResolver
    from app.services.entity_resolution.models import RepositoryNode

    # Verify user has access to this repo
    repo_result = await db.execute(
        select(Repo).where(Repo.id == UUID(repo_id), Repo.user_id == current_user.id)
    )
    repo = repo_result.scalar_one_or_none()
    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found")

    # Extract simulation parameters
    query = body.get("query")
    change_type = body.get("change_type")
    target_name = body.get("target_name")
    target_type = body.get("target_type")
    max_depth = body.get("max_depth", 5)

    # Use Entity Resolution if query is provided
    if query:
        entity_resolver = EntityResolver()
        resolved_node, resolved_action, resolution = await entity_resolver.resolve_with_action(
            db=db,
            repo_id=repo_id,
            query=query
        )

        if not resolved_node:
            return {
                "success": False,
                "error": resolution.error_message,
                "suggested_matches": resolution.suggested_matches,
                "target_not_found": True
            }

        # Use resolved values
        target_node = resolved_node
        change_type = change_type or resolved_action or "delete"
    else:
        # Legacy mode: use direct parameters (for backward compatibility)
        if not target_name:
            raise HTTPException(status_code=400, detail="target_name is required")

        # Validate change type
        valid_change_types = ["delete", "rename", "move", "extract", "add"]
        if change_type not in valid_change_types:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid change_type. Must be one of: {', '.join(valid_change_types)}"
            )

        # Create a RepositoryNode from the parameters
        target_node = RepositoryNode(
            id=UUID("00000000-0000-0000-0000-000000000000"),  # Placeholder ID
            name=target_name,
            node_type=target_type or "unknown",
            repo_id=UUID(repo_id)
        )

    # Run simulation
    engine = ChangeSimulationEngine()
    result = await engine.simulate_change(
        db=db,
        target_node=target_node,
        change_type=change_type,
        max_depth=max_depth
    )

    return result
