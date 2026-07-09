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


@router.post("/api/repos/{repo_id}/migration-plan")
async def generate_migration_plan(
    repo_id: str,
    body: dict,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Generate deterministic migration plan from Engineering Evidence."""
    from app.services.engineering_evidence.pipeline_integration import EngineeringEvidenceService
    from app.services.entity_resolution.entity_resolver import EntityResolver

    # Verify user has access to this repo
    repo_result = await db.execute(
        select(Repo).where(Repo.id == UUID(repo_id), Repo.user_id == current_user.id)
    )
    repo = repo_result.scalar_one_or_none()
    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found")

    # Extract parameters
    query = body.get("query")
    target_name = body.get("target_name")
    target_type = body.get("target_type", "unknown")
    change_type = body.get("change_type", "delete")

    # Resolve target
    if query:
        entity_resolver = EntityResolver()
        resolved_node, resolved_action, resolution = await entity_resolver.resolve_with_action(
            db=db,
            repo_id=repo_id,
            query=query
        )
        if not resolved_node:
            raise HTTPException(status_code=404, detail="Target not found")
        target_name = resolved_node.name
        target_type = resolved_node.node_type
        change_type = change_type or resolved_action or "delete"

    # Generate Engineering Evidence
    evidence_service = EngineeringEvidenceService()
    evidence = await evidence_service.generate_evidence(
        repo_id=UUID(repo_id),
        target_name=target_name,
        target_type=target_type,
        db=db
    )

    # Generate deterministic migration plan based on evidence
    steps = []
    step_number = 1

    # Step 1: Deprecate (if critical)
    if evidence.overall_criticality.value in ["CRITICAL", "HIGH"]:
        steps.append({
            "step": step_number,
            "title": "Deprecate Target",
            "description": f"Mark {target_name} as deprecated with clear deprecation notice",
            "actions": [
                f"Add deprecation warning to {target_name}",
                "Update documentation to reflect deprecation",
                "Notify dependent teams of deprecation timeline"
            ],
            "estimated_time": "1-2 hours",
            "status": "pending"
        })
        step_number += 1

    # Step 2: Move callers (if runtime dependencies)
    if evidence.runtime and evidence.runtime.reference_count > 0:
        steps.append({
            "step": step_number,
            "title": "Migrate Callers",
            "description": f"Update {evidence.runtime.reference_count} runtime callers to use alternative implementation",
            "actions": [
                f"Update {evidence.runtime.critical_count} critical callers first",
                "Update remaining callers",
                "Verify all callers are migrated"
            ],
            "estimated_time": f"{evidence.runtime.reference_count * 0.5} hours",
            "status": "pending"
        })
        step_number += 1

    # Step 3: Update imports (if internal service dependencies)
    if evidence.internal_service and evidence.internal_service.reference_count > 0:
        steps.append({
            "step": step_number,
            "title": "Update Imports",
            "description": f"Update {evidence.internal_service.reference_count} import statements",
            "actions": [
                "Find and replace import statements",
                "Update module references",
                "Verify no broken imports remain"
            ],
            "estimated_time": f"{evidence.internal_service.reference_count * 0.25} hours",
            "status": "pending"
        })
        step_number += 1

    # Step 4: Update configuration (if configuration dependencies)
    if evidence.configuration and evidence.configuration.reference_count > 0:
        steps.append({
            "step": step_number,
            "title": "Update Configuration",
            "description": f"Update {evidence.configuration.reference_count} configuration references",
            "actions": [
                "Update environment variables",
                "Update config files",
                "Update documentation"
            ],
            "estimated_time": f"{evidence.configuration.reference_count * 0.5} hours",
            "status": "pending"
        })
        step_number += 1

    # Step 5: Run tests (if testing dependencies)
    if evidence.testing and evidence.testing.reference_count > 0:
        steps.append({
            "step": step_number,
            "title": "Run Tests",
            "description": f"Run {evidence.testing.reference_count} related tests to verify migration",
            "actions": [
                "Run unit tests",
                "Run integration tests",
                "Run API tests",
                "Verify all tests pass"
            ],
            "estimated_time": "1-2 hours",
            "status": "pending"
        })
        step_number += 1

    # Step 6: Delete (final step)
    steps.append({
        "step": step_number,
        "title": "Delete Target",
        "description": f"Remove {target_name} from codebase",
        "actions": [
            f"Delete {target_name} implementation",
            "Delete associated tests",
            "Update documentation"
        ],
        "estimated_time": "30 minutes",
        "status": "pending"
    })

    # Add validation steps from evidence
    if evidence.recommended_validation_steps:
        steps.append({
            "step": step_number + 1,
            "title": "Validation Steps",
            "description": "Post-migration validation",
            "actions": evidence.recommended_validation_steps,
            "estimated_time": "1-2 hours",
            "status": "pending"
        })

    return {
        "target_name": target_name,
        "target_type": target_type,
        "change_type": change_type,
        "overall_criticality": evidence.overall_criticality.value,
        "total_references": evidence.total_references,
        "steps": steps,
        "estimated_total_time": sum(
            float(s["estimated_time"].split("-")[0].strip().replace(" hours", "").replace(" hour", "").replace(" minutes", "").replace(" minute", ""))
            for s in steps
            if s["estimated_time"]
        )
    }


@router.post("/api/repos/{repo_id}/testing-checklist")
async def generate_testing_checklist(
    repo_id: str,
    body: dict,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Generate testing checklist from Engineering Evidence."""
    from app.services.engineering_evidence.pipeline_integration import EngineeringEvidenceService
    from app.services.entity_resolution.entity_resolver import EntityResolver

    # Verify user has access to this repo
    repo_result = await db.execute(
        select(Repo).where(Repo.id == UUID(repo_id), Repo.user_id == current_user.id)
    )
    repo = repo_result.scalar_one_or_none()
    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found")

    # Extract parameters
    query = body.get("query")
    target_name = body.get("target_name")
    target_type = body.get("target_type", "unknown")

    # Resolve target
    if query:
        entity_resolver = EntityResolver()
        resolved_node, _, resolution = await entity_resolver.resolve_with_action(
            db=db,
            repo_id=repo_id,
            query=query
        )
        if not resolved_node:
            raise HTTPException(status_code=404, detail="Target not found")
        target_name = resolved_node.name
        target_type = resolved_node.node_type

    # Generate Engineering Evidence
    evidence_service = EngineeringEvidenceService()
    evidence = await evidence_service.generate_evidence(
        repo_id=UUID(repo_id),
        target_name=target_name,
        target_type=target_type,
        db=db
    )

    # Generate testing checklist based on evidence
    checklist = {
        "target_name": target_name,
        "target_type": target_type,
        "overall_criticality": evidence.overall_criticality.value,
        "total_references": evidence.total_references,
        "unit_tests": [],
        "integration_tests": [],
        "api_tests": [],
        "database_validation": [],
        "deployment_verification": [],
        "regression_tests": []
    }

    # Unit tests based on affected systems
    if evidence.runtime and evidence.runtime.affected_systems:
        for system in evidence.runtime.affected_systems[:5]:
            checklist["unit_tests"].append({
                "test_name": f"test_{system.lower().replace(' ', '_')}_with_target_removed",
                "description": f"Test {system} behavior without {target_name}",
                "priority": "high" if evidence.runtime.criticality.value == "CRITICAL" else "medium",
                "status": "pending"
            })

    # Integration tests based on evidence groups
    if evidence.database:
        checklist["integration_tests"].append({
            "test_name": "test_database_operations_without_target",
            "description": f"Test database operations without {target_name}",
            "priority": "high" if evidence.database.criticality.value == "CRITICAL" else "medium",
            "status": "pending"
        })

    if evidence.public_api:
        checklist["integration_tests"].append({
            "test_name": "test_api_endpoints_without_target",
            "description": f"Test API endpoints without {target_name}",
            "priority": "high" if evidence.public_api.criticality.value == "CRITICAL" else "medium",
            "status": "pending"
        })

    # API tests based on public API evidence
    if evidence.public_api and evidence.public_api.reference_count > 0:
        for i in range(min(evidence.public_api.reference_count, 3)):
            checklist["api_tests"].append({
                "test_name": f"test_api_endpoint_{i + 1}_without_target",
                "description": f"Test API endpoint {i + 1} behavior without {target_name}",
                "priority": "high",
                "status": "pending"
            })

    # Database validation based on database evidence
    if evidence.database and evidence.database.reference_count > 0:
        checklist["database_validation"].append({
            "test_name": "test_database_schema_consistency",
            "description": "Verify database schema remains consistent after change",
            "priority": "high" if evidence.database.criticality.value == "CRITICAL" else "medium",
            "status": "pending"
        })
        checklist["database_validation"].append({
            "test_name": "test_foreign_key_constraints",
            "description": "Verify foreign key constraints are not violated",
            "priority": "high",
            "status": "pending"
        })

    # Deployment verification based on deployment risk
    if evidence.deployment_risk:
        checklist["deployment_verification"].append({
            "test_name": "test_deployment_rollback",
            "description": "Test rollback procedure if deployment fails",
            "priority": "high" if evidence.deployment_risk.risk_level.value == "CRITICAL" else "medium",
            "status": "pending"
        })
        checklist["deployment_verification"].append({
            "test_name": "test_deployment_configuration",
            "description": "Verify deployment configuration is correct",
            "priority": "medium",
            "status": "pending"
        })

    # Regression tests based on affected systems
    if evidence.affected_systems:
        for system in evidence.affected_systems[:3]:
            checklist["regression_tests"].append({
                "test_name": f"test_{system.lower().replace(' ', '_')}_regression",
                "description": f"Regression test for {system} to ensure no unexpected behavior",
                "priority": "medium",
                "status": "pending"
            })

    # Add evidence-based validation steps
    for step in evidence.recommended_validation_steps[:3]:
        checklist["regression_tests"].append({
            "test_name": f"test_validation_step",
            "description": step,
            "priority": "high",
            "status": "pending"
        })

    return checklist
