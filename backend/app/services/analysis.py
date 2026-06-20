import asyncio
import logging
import os
import time
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

# ── Cleanup tuning ────────────────────────────────────────────────────
# Re-analysis must delete the repo's prior graph. A single
# `DELETE FROM edges WHERE repo_id = ?` removing tens of thousands of rows
# exceeds Postgres/Supabase statement_timeout and raises QueryCanceledError.
# We delete in small committed batches so each statement stays well under the
# timeout and locks are released between batches.
DELETE_BATCH_SIZE = int(os.getenv("ANALYSIS_DELETE_BATCH_SIZE", "1000"))
DELETE_MAX_RETRIES = int(os.getenv("ANALYSIS_DELETE_RETRIES", "3"))
DELETE_RETRY_BASE_DELAY = 0.5  # seconds; exponential backoff

# Statuses that mean analysis produced a usable graph. Both must be treated as
# "ready" by any read path (impact, repo detail, workflows, frontend gates).
# "completed_with_warnings" = the graph was built, but some files were skipped.
ANALYZED_STATUSES: tuple[str, ...] = ("completed", "completed_with_warnings")

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

            cleanup_clean = await _clear_repo_analysis(db, repo.id)

            payload: AnalysisPayload = await asyncio.wait_for(
                asyncio.to_thread(collect_analysis_payload, clone_path),
                timeout=ANALYSIS_TIMEOUT_SECONDS,
            )
            stats = await _persist_analysis(db, repo, payload)

            failed_count = len(payload.failed_files)
            # A single unparseable file, or a cleanup that timed out, must NEVER
            # fail the repo. "failed" is reserved for clone failure / DB
            # unavailable / repo inaccessible (handled in the except blocks below).
            has_warnings = bool(failed_count) or not cleanup_clean
            repo.total_files = stats["total_files"]
            repo.total_functions = stats["total_functions"]
            repo.total_lines = stats["total_lines"]
            repo.analysis_status = (
                "completed_with_warnings" if has_warnings else "completed"
            )
            repo.last_analyzed_at = datetime.now(timezone.utc)
            await db.commit()

            if has_warnings:
                logger.warning(
                    "Analysis completed_with_warnings for %s: %d file(s) skipped, "
                    "cleanup_clean=%s",
                    repo.full_name,
                    failed_count,
                    cleanup_clean,
                )

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


async def _delete_batch_with_retry(db: AsyncSession, model, repo_id: UUID, batch_size: int) -> int:
    """Delete up to `batch_size` rows of `model` for a repo, with retry.

    Returns the number of rows deleted in this batch. Each successful batch is
    committed so locks are released and the statement_timeout clock resets.
    """
    # DELETE ... WHERE id IN (SELECT id ... WHERE repo_id = ? LIMIT N)
    ids_subq = (
        select(model.id).where(model.repo_id == repo_id).limit(batch_size)
    )
    stmt = delete(model).where(model.id.in_(ids_subq))

    last_exc: Exception | None = None
    for attempt in range(1, DELETE_MAX_RETRIES + 1):
        try:
            result = await db.execute(stmt)
            await db.commit()
            return result.rowcount or 0
        except Exception as exc:  # transient timeout / disconnect → retry
            last_exc = exc
            await db.rollback()
            logger.warning(
                "DELETE %s batch failed (attempt %d/%d): %s",
                model.__tablename__, attempt, DELETE_MAX_RETRIES, exc,
            )
            if attempt < DELETE_MAX_RETRIES:
                await asyncio.sleep(DELETE_RETRY_BASE_DELAY * (2 ** (attempt - 1)))
    assert last_exc is not None
    raise last_exc


async def _delete_table_in_batches(db: AsyncSession, model, repo_id: UUID) -> int:
    """Delete all of a repo's rows for `model` in committed batches."""
    start = time.perf_counter()
    total = 0
    while True:
        deleted = await _delete_batch_with_retry(db, model, repo_id, DELETE_BATCH_SIZE)
        total += deleted
        if deleted < DELETE_BATCH_SIZE:
            break
    logger.info(
        "Cleared %s: %d row(s) in %.3fs (batch=%d)",
        model.__tablename__, total, time.perf_counter() - start, DELETE_BATCH_SIZE,
    )
    return total


async def _clear_repo_analysis(db: AsyncSession, repo_id: UUID) -> bool:
    """Remove a repo's prior analysis in safe, committed batches.

    Returns True if cleanup completed cleanly, or False if any table could not be
    fully cleared (the caller marks the run completed_with_warnings). This function
    NEVER raises: a cleanup timeout must not fail the whole analysis.

    Order matters — edges reference nodes, so clearing edges first avoids extra
    cascade work when nodes are removed.
    """
    overall_start = time.perf_counter()
    clean = True
    for model in (Edge, Node, RepoFile, FolderTree):
        try:
            await _delete_table_in_batches(db, model, repo_id)
        except Exception:
            # Batched delete failed — try a single brute-force DELETE as fallback
            logger.warning(
                "Batched cleanup of %s failed; trying single DELETE fallback",
                model.__tablename__, exc_info=True,
            )
            try:
                await db.rollback()
                await db.execute(delete(model).where(model.repo_id == repo_id))
                await db.commit()
            except Exception:
                clean = False
                logger.error(
                    "Cleanup of %s for repo %s did not fully complete; continuing analysis",
                    model.__tablename__, repo_id, exc_info=True,
                )
                try:
                    await db.rollback()
                except Exception:
                    pass
    logger.info(
        "Repo %s cleanup finished in %.3fs (clean=%s)",
        repo_id, time.perf_counter() - overall_start, clean,
    )
    return clean


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

    # Deduplicate nodes by full_path (safety net — collector should already
    # deduplicate, but the DB unique constraint is fatal if any slip through).
    seen_paths: dict[str, dict] = {}
    for n in payload.nodes:
        seen_paths[n["full_path"]] = n  # last wins
    unique_nodes = list(seen_paths.values())

    node_models: list[Node] = []
    for n in unique_nodes:
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
    seen_edge_keys: set[tuple[str, str, str]] = set()
    for e in payload.edges:
        from_id = path_to_node_id.get(e["from_path"])
        to_id = path_to_node_id.get(e["to_path"])
        if not from_id or not to_id:
            continue
        edge_key = (str(from_id), str(to_id), e["edge_type"])
        if edge_key in seen_edge_keys:
            continue
        seen_edge_keys.add(edge_key)
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

