import asyncio
import logging
from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Edge, FolderTree, Node, Repo, RepoFile, User
from app.services.analysis_collect import AnalysisPayload, collect_analysis_payload
from app.services.repo_fetcher import cleanup_clone, clone_github_repo
from app.utils.github import get_github_token

logger = logging.getLogger(__name__)

ANALYSIS_TIMEOUT_SECONDS = 600
STALE_ANALYSIS_MINUTES = 3

_active_analyses: set[str] = set()


def is_analysis_running(repo_id: UUID | str) -> bool:
    return str(repo_id) in _active_analyses


def _repo_updated_at_utc(repo: Repo) -> datetime:
    updated = repo.updated_at
    if updated.tzinfo is None:
        return updated.replace(tzinfo=timezone.utc)
    return updated


def is_stale_in_progress(repo: Repo) -> bool:
    if repo.analysis_status not in ("analyzing", "queued"):
        return False
    if is_analysis_running(repo.id):
        return False
    age = datetime.now(timezone.utc) - _repo_updated_at_utc(repo)
    return age > timedelta(minutes=STALE_ANALYSIS_MINUTES)


async def recover_stale_analysis(db: AsyncSession, repo: Repo) -> bool:
    """Mark stuck queued/analyzing repos as failed when no worker is running."""
    if not is_stale_in_progress(repo):
        return False
    logger.warning("Recovering stale analysis for %s (was %s)", repo.full_name, repo.analysis_status)
    repo.analysis_status = "failed"
    await db.flush()
    return True


async def run_repo_analysis(repo_id: UUID, user_id: UUID) -> None:
    repo_key = str(repo_id)
    if repo_key in _active_analyses:
        logger.info("Analysis already running for repo %s", repo_id)
        return

    _active_analyses.add(repo_key)
    clone_path: str | None = None

    from app.database import async_session_factory

    async with async_session_factory() as db:
        try:
            result = await db.execute(
                select(Repo).where(Repo.id == repo_id, Repo.user_id == user_id)
            )
            repo = result.scalar_one_or_none()
            if not repo:
                logger.error("Repo %s not found for analysis", repo_id)
                return

            user_result = await db.execute(select(User).where(User.id == user_id))
            user = user_result.scalar_one_or_none()
            if not user:
                logger.error("User %s not found for analysis", user_id)
                return

            token = await get_github_token(user, db)
            if not token:
                repo.analysis_status = "failed"
                await db.commit()
                return

            repo.analysis_status = "analyzing"
            await db.commit()

            clone_path = await asyncio.to_thread(
                clone_github_repo,
                repo.full_name,
                token,
                repo.default_branch,
            )

            await _clear_repo_analysis(db, repo.id)

            payload: AnalysisPayload = await asyncio.wait_for(
                asyncio.to_thread(collect_analysis_payload, clone_path),
                timeout=ANALYSIS_TIMEOUT_SECONDS,
            )
            stats = await _persist_analysis(db, repo, payload)

            repo.total_files = stats["total_files"]
            repo.total_functions = stats["total_functions"]
            repo.total_lines = stats["total_lines"]
            repo.analysis_status = "completed"
            repo.last_analyzed_at = datetime.now(timezone.utc)
            await db.commit()

            try:
                from app.services.alias_seeder import (
                    index_node_embeddings,
                    link_workflow_aliases_to_nodes,
                    seed_aliases_for_repo,
                )

                await seed_aliases_for_repo(repo.id, db)
                await link_workflow_aliases_to_nodes(repo.id, db)
                await index_node_embeddings(repo.id, db)
                await db.commit()
            except Exception:
                await db.rollback()
                logger.warning(
                    "Alias/embedding seed skipped for %s",
                    repo_id,
                    exc_info=True,
                )

            try:
                from app.services.workflow_discovery_service import (
                    WorkflowDiscoveryService,
                )

                wf_count = await WorkflowDiscoveryService().discover_for_repo(
                    repo.id, db
                )
                await db.commit()
                logger.info(
                    "Workflow discovery for %s: %d workflows",
                    repo.full_name,
                    wf_count,
                )
            except Exception:
                await db.rollback()
                logger.warning(
                    "Workflow discovery skipped for %s",
                    repo_id,
                    exc_info=True,
                )

            try:
                from app.services.critical_path_service import CriticalPathService
                from app.services.impact_precompute_service import ImpactPrecomputeService

                await CriticalPathService().seed_for_repo(repo.id, db)
                metric_count = await ImpactPrecomputeService().recompute_for_repo(
                    repo.id, db
                )
                await db.commit()
                logger.info(
                    "Impact precompute for %s: %d node metrics",
                    repo.full_name,
                    metric_count,
                )
            except Exception:
                await db.rollback()
                logger.warning(
                    "Impact precompute skipped for %s",
                    repo_id,
                    exc_info=True,
                )

            logger.info(
                "Analysis completed for %s: %d files, %d functions",
                repo_id,
                stats["total_files"],
                stats["total_functions"],
            )
        except asyncio.TimeoutError:
            logger.error("Analysis timed out for repo %s", repo_id)
            await db.rollback()
            result = await db.execute(select(Repo).where(Repo.id == repo_id))
            repo = result.scalar_one_or_none()
            if repo:
                repo.analysis_status = "failed"
                await db.commit()
        except Exception:
            logger.exception("Analysis failed for repo %s", repo_id)
            await db.rollback()
            result = await db.execute(select(Repo).where(Repo.id == repo_id))
            repo = result.scalar_one_or_none()
            if repo:
                repo.analysis_status = "failed"
                await db.commit()
        finally:
            if clone_path:
                await asyncio.to_thread(cleanup_clone, clone_path)
            _active_analyses.discard(repo_key)


async def _clear_repo_analysis(db: AsyncSession, repo_id: UUID) -> None:
    await db.execute(delete(Edge).where(Edge.repo_id == repo_id))
    await db.execute(delete(Node).where(Node.repo_id == repo_id))
    await db.execute(delete(RepoFile).where(RepoFile.repo_id == repo_id))
    await db.execute(delete(FolderTree).where(FolderTree.repo_id == repo_id))
    await db.flush()


async def _persist_analysis(db: AsyncSession, repo: Repo, payload: AnalysisPayload) -> dict:
    file_models: list[RepoFile] = []
    for f in payload.files:
        file_models.append(RepoFile(repo_id=repo.id, **f))
    db.add_all(file_models)
    await db.flush()

    path_to_file_id = {fm.file_path: fm.id for fm in file_models}

    folder_models = [FolderTree(repo_id=repo.id, **folder) for folder in payload.folders]
    db.add_all(folder_models)
    await db.flush()

    node_models: list[Node] = []
    for n in payload.nodes:
        file_id = path_to_file_id.get(n["file_path"])
        node_models.append(
            Node(
                repo_id=repo.id,
                file_id=file_id,
                node_type=n["node_type"],
                name=n["name"],
                full_path=n["full_path"],
                start_line=n["start_line"],
                end_line=n["end_line"],
                raw_code=n.get("raw_code"),
                signature=n.get("signature"),
                calls=n.get("calls", []),
                imports=n.get("imports", []),
                is_exported=n.get("is_exported", False),
                is_async=n.get("is_async", False),
                http_method=n.get("http_method"),
                route_path=n.get("route_path"),
            )
        )
    db.add_all(node_models)
    await db.flush()

    path_to_node_id = {nm.full_path: nm.id for nm in node_models}
    edge_models: list[Edge] = []
    for e in payload.edges:
        from_id = path_to_node_id.get(e["from_path"])
        to_id = path_to_node_id.get(e["to_path"])
        if not from_id or not to_id:
            continue
        edge_models.append(
            Edge(
                repo_id=repo.id,
                from_node_id=from_id,
                to_node_id=to_id,
                edge_type=e["edge_type"],
            )
        )
    if edge_models:
        db.add_all(edge_models)

    return {
        "total_files": payload.total_files,
        "total_functions": payload.total_functions,
        "total_lines": payload.total_lines,
    }
