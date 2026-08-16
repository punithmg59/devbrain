import asyncio
import logging
import os
import time
from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Edge, FolderTree, Node, Repo, RepoFile, User
from app.services.repo_fetcher import cleanup_clone, clone_github_repo
from app.services.v2_analyzer_adapter import run_v2_analysis_collection, AnalysisPayloadV2
from app.utils.github import get_github_token
from app.security.encryption import get_encryption_service, EncryptionError

logger = logging.getLogger(__name__)

ANALYSIS_TIMEOUT_SECONDS = 600
STALE_ANALYSIS_MINUTES = 3

# ── New: per-stage timeouts configurable via env ──────────────────────────────
# Clone timeout: gitpython has no built-in timeout; we enforce it here.
CLONE_TIMEOUT_SECONDS = int(os.getenv("ANALYSIS_CLONE_TIMEOUT_SECONDS", "120"))

# Persist timeout: covers the db.flush() calls for files/nodes/edges.
PERSIST_TIMEOUT_SECONDS = int(os.getenv("ANALYSIS_PERSIST_TIMEOUT_SECONDS", "180"))

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


async def run_repo_analysis(repo_id: UUID, user_id: UUID) -> bool:
    """Run full analysis for a repository.

    Returns True if analysis completed (or completed_with_warnings).
    Returns False if skipped (already running, not found, error).
    """
    repo_key = str(repo_id)
    if repo_key in _active_analyses:
        logger.info("[ANALYSIS] job_skipped repo_id=%s reason=already_running", repo_id)
        return False

    _active_analyses.add(repo_key)
    clone_path: str | None = None
    run_start = time.monotonic()

    logger.info("[ANALYSIS] job_started repo_id=%s", repo_id)

    from app.database import async_session_factory

    async with async_session_factory() as db:
        try:
            result = await db.execute(
                select(Repo).where(Repo.id == repo_id, Repo.user_id == user_id)
            )
            repo = result.scalar_one_or_none()
            if not repo:
                logger.error("[ANALYSIS] job_aborted repo_id=%s reason=repo_not_found", repo_id)
                return False

            user_result = await db.execute(select(User).where(User.id == user_id))
            user = user_result.scalar_one_or_none()
            if not user:
                logger.error("[ANALYSIS] job_aborted repo_id=%s reason=user_not_found user_id=%s", repo_id, user_id)
                return False

            token = await get_github_token(user, db)
            if not token:
                logger.error("[ANALYSIS] job_aborted repo_id=%s reason=no_github_token", repo_id)
                repo.analysis_status = "failed"
                await db.commit()
                return False

            repo.analysis_status = "analyzing"
            await db.commit()

            # ── STAGE: clone ─────────────────────────────────────────────────
            # CRITICAL FIX: gitpython clone_from() has no built-in timeout.
            # Without asyncio.wait_for, a stalled network connection blocks
            # this thread permanently, causing the job to hang forever while
            # the frontend keeps polling the "analyzing" status.
            t0 = time.monotonic()
            logger.info(
                "[ANALYSIS] clone_started repo_id=%s full_name=%s timeout=%ds",
                repo_id, repo.full_name, CLONE_TIMEOUT_SECONDS,
            )
            try:
                clone_path = await asyncio.wait_for(
                    asyncio.to_thread(
                        clone_github_repo,
                        repo.full_name,
                        token,
                        repo.default_branch,
                    ),
                    timeout=CLONE_TIMEOUT_SECONDS,
                )
            except asyncio.TimeoutError:
                elapsed = time.monotonic() - t0
                logger.error(
                    "[ANALYSIS] clone_timeout repo_id=%s elapsed=%.1fs timeout=%ds",
                    repo_id, elapsed, CLONE_TIMEOUT_SECONDS,
                )
                raise  # caught by the outer asyncio.TimeoutError handler
            logger.info(
                "[ANALYSIS] clone_completed repo_id=%s elapsed=%.1fs",
                repo_id, time.monotonic() - t0,
            )

            # ── STAGE: clear prior analysis ───────────────────────────────────
            t0 = time.monotonic()
            logger.info("[ANALYSIS] clear_started repo_id=%s", repo_id)
            cleanup_clean = await _clear_repo_analysis(db, repo.id)
            logger.info(
                "[ANALYSIS] clear_completed repo_id=%s elapsed=%.1fs clean=%s",
                repo_id, time.monotonic() - t0, cleanup_clean,
            )

            # ── STAGE: v2 collection ──────────────────────────────────────────
            t0 = time.monotonic()
            logger.info(
                "[ANALYSIS] v2_collection_started repo_id=%s timeout=%ds",
                repo_id, ANALYSIS_TIMEOUT_SECONDS,
            )
            payload = await asyncio.wait_for(
                asyncio.to_thread(run_v2_analysis_collection, clone_path, str(repo.id)),
                timeout=ANALYSIS_TIMEOUT_SECONDS,
            )
            logger.info(
                "[ANALYSIS] v2_collection_completed repo_id=%s files=%d nodes=%d edges=%d elapsed=%.1fs",
                repo_id,
                payload.total_files,
                len(payload.nodes),
                len(payload.edges),
                time.monotonic() - t0,
            )

            # ── STAGE: persist ────────────────────────────────────────────────
            # CRITICAL FIX: _persist_analysis has multiple db.flush() calls
            # that can stall on DB slowdowns. Enforce a hard timeout.
            t0 = time.monotonic()
            logger.info(
                "[ANALYSIS] persist_started repo_id=%s nodes=%d edges=%d timeout=%ds",
                repo_id, len(payload.nodes), len(payload.edges), PERSIST_TIMEOUT_SECONDS,
            )
            stats = await asyncio.wait_for(
                _persist_analysis(db, repo, payload),
                timeout=PERSIST_TIMEOUT_SECONDS,
            )
            logger.info(
                "[ANALYSIS] persist_completed repo_id=%s files=%d functions=%d elapsed=%.1fs",
                repo_id, stats["total_files"], stats["total_functions"],
                time.monotonic() - t0,
            )

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
            repo.has_completed_analysis = True
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

            # ── STAGE: alias seeding ──────────────────────────────────────────
            t0 = time.monotonic()
            logger.info("[ANALYSIS] alias_seed_started repo_id=%s", repo_id)
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
                logger.info(
                    "[ANALYSIS] alias_seed_completed repo_id=%s elapsed=%.1fs",
                    repo_id, time.monotonic() - t0,
                )
            except Exception:
                await db.rollback()
                logger.warning(
                    "[ANALYSIS] alias_seed_skipped repo_id=%s elapsed=%.1fs",
                    repo_id, time.monotonic() - t0,
                    exc_info=True,
                )

            # ── STAGE: workflow discovery ─────────────────────────────────────
            t0 = time.monotonic()
            logger.info("[ANALYSIS] workflow_discovery_started repo_id=%s", repo_id)
            try:
                from app.services.workflow_discovery_service import (
                    WorkflowDiscoveryService,
                )

                wf_count = await WorkflowDiscoveryService().discover_for_repo(
                    repo.id, db
                )
                await db.commit()
                logger.info(
                    "[ANALYSIS] workflow_discovery_completed repo_id=%s workflows=%d elapsed=%.1fs",
                    repo_id, wf_count, time.monotonic() - t0,
                )
            except Exception:
                await db.rollback()
                logger.warning(
                    "[ANALYSIS] workflow_discovery_skipped repo_id=%s elapsed=%.1fs",
                    repo_id, time.monotonic() - t0,
                    exc_info=True,
                )

            # ── STAGE: impact precompute ──────────────────────────────────────
            t0 = time.monotonic()
            logger.info("[ANALYSIS] impact_precompute_started repo_id=%s", repo_id)
            try:
                from app.services.critical_path_service import CriticalPathService
                from app.services.impact_precompute_service import ImpactPrecomputeService

                await CriticalPathService().seed_for_repo(repo.id, db)
                metric_count = await ImpactPrecomputeService().recompute_for_repo(
                    repo.id, db
                )
                await db.commit()
                logger.info(
                    "[ANALYSIS] impact_precompute_completed repo_id=%s metrics=%d elapsed=%.1fs",
                    repo_id, metric_count, time.monotonic() - t0,
                )
            except Exception:
                await db.rollback()
                logger.warning(
                    "[ANALYSIS] impact_precompute_skipped repo_id=%s elapsed=%.1fs",
                    repo_id, time.monotonic() - t0,
                    exc_info=True,
                )

            total_elapsed = time.monotonic() - run_start
            logger.info(
                "[ANALYSIS] job_completed repo_id=%s files=%d functions=%d elapsed=%.1fs",
                repo_id,
                stats["total_files"],
                stats["total_functions"],
                total_elapsed,
            )
            return True

        except asyncio.TimeoutError:
            elapsed = time.monotonic() - run_start
            logger.error(
                "[ANALYSIS] job_timeout repo_id=%s elapsed=%.1fs",
                repo_id, elapsed,
            )
            await db.rollback()
            result = await db.execute(select(Repo).where(Repo.id == repo_id))
            repo = result.scalar_one_or_none()
            if repo:
                repo.analysis_status = "failed"
                await db.commit()
            return False

        except Exception:
            elapsed = time.monotonic() - run_start
            logger.exception(
                "[ANALYSIS] job_failed repo_id=%s elapsed=%.1fs",
                repo_id, elapsed,
            )
            await db.rollback()
            result = await db.execute(select(Repo).where(Repo.id == repo_id))
            repo = result.scalar_one_or_none()
            if repo:
                repo.analysis_status = "failed"
                await db.commit()
            return False

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


async def _persist_analysis(db: AsyncSession, repo: Repo, payload: AnalysisPayloadV2) -> dict:
    encryption_service = get_encryption_service()
    repo_context = str(repo.id).encode('utf-8')
    
    file_models: list[RepoFile] = []
    for f in payload.files:
        # Encrypt content_preview if present
        content_preview = f.get("content_preview")
        content_preview_encrypted = None
        
        if content_preview:
            try:
                content_preview_encrypted = await encryption_service.encrypt(
                    content_preview,
                    associated_data=repo_context,
                )
                # Clear plaintext after encryption
                f["content_preview"] = None
            except EncryptionError as e:
                logger.error("Failed to encrypt content_preview for %s: %s", f["file_path"], e)
                # Fall back to not storing preview rather than storing plaintext
                f["content_preview"] = None
        
        file_data = {**f, "content_preview_encrypted": content_preview_encrypted}
        file_models.append(RepoFile(repo_id=repo.id, **file_data))
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
        
        # Encrypt raw_code if present
        raw_code = n.get("raw_code")
        raw_code_encrypted = None
        
        if raw_code:
            try:
                raw_code_encrypted = await encryption_service.encrypt(
                    raw_code,
                    associated_data=repo_context,
                )
                # Clear plaintext after encryption
                raw_code = None
            except EncryptionError as e:
                logger.error("Failed to encrypt raw_code for %s: %s", n["full_path"], e)
                # Fall back to not storing code rather than storing plaintext
                raw_code = None
        
        node_models.append(
            Node(
                repo_id=repo.id,
                file_id=file_id,
                node_type=n["node_type"],
                name=n["name"],
                full_path=n["full_path"],
                start_line=n["start_line"],
                end_line=n["end_line"],
                raw_code=raw_code,
                raw_code_encrypted=raw_code_encrypted,
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
