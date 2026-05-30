"""Repo-detail router — file tree, file/node browsing, stats, Groq summaries."""

from __future__ import annotations

import asyncio
import logging
from collections import defaultdict
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from fastapi.responses import JSONResponse
from sqlalchemy import func as sa_func, select, case, literal_column
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Edge, Node, Repo, RepoFile, FolderTree, User
from app.schemas.repo_detail import (
    ApiRoutesResponse,
    BatchSummarizeResponse,
    FileDetailResponse,
    FileResponse,
    FileTreeNode,
    NodeDetailResponse,
    NodeRelation,
    NodeResponse,
    NodeSummaryResponse,
    PaginatedFilesResponse,
    PaginatedNodesResponse,
    RepoStatsResponse,
)
from app.utils.auth import get_current_user
from app.utils.groq_client import generate_node_summary

logger = logging.getLogger(__name__)
router = APIRouter(tags=["repo-detail"])


# ── Helpers ─────────────────────────────────────────────────────

async def _get_user_repo(
    repo_id: str,
    current_user: User,
    db: AsyncSession,
) -> Repo:
    """Load a repo, verifying ownership. Raises 404 if missing/not owned."""
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


def _require_completed(repo: Repo) -> None:
    """Return HTTP 400 if analysis is not complete."""
    if repo.analysis_status != "completed":
        raise HTTPException(
            status_code=400,
            detail={
                "error": "Analysis not complete",
                "status": repo.analysis_status,
            },
        )


def _file_to_response(f: RepoFile, *, include_preview: bool = False) -> FileResponse:
    return FileResponse(
        id=str(f.id),
        repo_id=str(f.repo_id),
        file_path=f.file_path,
        file_name=f.file_name,
        extension=f.extension,
        language=f.language,
        folder_path=f.folder_path,
        depth=f.depth,
        size_bytes=f.size_bytes,
        line_count=f.line_count,
        content_preview=f.content_preview if include_preview else None,
        importance_score=f.importance_score,
    )


def _node_to_response(n: Node, *, include_code: bool = False) -> NodeResponse:
    return NodeResponse(
        id=str(n.id),
        repo_id=str(n.repo_id),
        file_id=str(n.file_id) if n.file_id else None,
        node_type=n.node_type,
        name=n.name,
        full_path=n.full_path,
        start_line=n.start_line,
        end_line=n.end_line,
        raw_code=n.raw_code if include_code else None,
        signature=n.signature,
        calls=n.calls or [],
        called_by=n.called_by or [],
        http_method=n.http_method,
        route_path=n.route_path,
        summary=n.summary,
        tags=n.tags or [],
        is_exported=n.is_exported,
        is_async=n.is_async,
        complexity_score=n.complexity_score,
    )


# ═══════════════════════════════════════════════════════════════
# GET /api/repos/{repo_id}/tree
# ═══════════════════════════════════════════════════════════════

@router.get("/api/repos/{repo_id}/tree")
async def get_file_tree(
    repo_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[FileTreeNode]:
    repo = await _get_user_repo(repo_id, current_user, db)
    _require_completed(repo)

    uid = repo.id

    # Two queries — no N+1
    folders_result = await db.execute(
        select(FolderTree)
        .where(FolderTree.repo_id == uid)
        .order_by(FolderTree.folder_path)
    )
    folders = list(folders_result.scalars().all())

    files_result = await db.execute(
        select(RepoFile)
        .where(RepoFile.repo_id == uid)
        .order_by(RepoFile.file_path)
    )
    files = list(files_result.scalars().all())

    # Build lookup: folder_path → FileTreeNode
    folder_nodes: dict[str, FileTreeNode] = {}
    for f in folders:
        node = FileTreeNode(
            id=str(f.id),
            name=f.folder_name,
            path=f.folder_path,
            type="folder",
            depth=f.depth,
            file_count=f.file_count,
            function_count=f.function_count,
        )
        folder_nodes[f.folder_path] = node

    # Place files into their parent folder
    file_nodes_by_folder: dict[str, list[FileTreeNode]] = defaultdict(list)
    for fi in files:
        fnode = FileTreeNode(
            id=str(fi.id),
            name=fi.file_name,
            path=fi.file_path,
            type="file",
            depth=fi.depth,
            extension=fi.extension,
            language=fi.language,
            line_count=fi.line_count,
        )
        file_nodes_by_folder[fi.folder_path].append(fnode)

    # Assemble children
    for path, ftn in folder_nodes.items():
        child_folders = sorted(
            [fn for fn in folder_nodes.values() if fn.path != path and _is_direct_child_folder(path, fn.path)],
            key=lambda x: x.name.lower(),
        )
        child_files = sorted(
            file_nodes_by_folder.get(path, []),
            key=lambda x: x.name.lower(),
        )
        ftn.children = child_folders + child_files

    # Root items: depth == 0 folders + depth == 0 files (root-level files)
    root_folders = sorted(
        [fn for fn in folder_nodes.values() if fn.depth == 0],
        key=lambda x: x.name.lower(),
    )
    root_files = sorted(
        file_nodes_by_folder.get("", []) + file_nodes_by_folder.get(".", []),
        key=lambda x: x.name.lower(),
    )

    tree = root_folders + root_files

    return JSONResponse(
        content=[t.model_dump() for t in tree],
        headers={"Cache-Control": "max-age=300"},
    )


def _is_direct_child_folder(parent_path: str, child_path: str) -> bool:
    """Check if child_path is a direct subfolder of parent_path."""
    if not parent_path or parent_path == ".":
        # Root level: direct child has no separator
        return "/" not in child_path and child_path != "."
    prefix = parent_path.rstrip("/") + "/"
    if not child_path.startswith(prefix):
        return False
    remainder = child_path[len(prefix):]
    return "/" not in remainder and len(remainder) > 0


# ═══════════════════════════════════════════════════════════════
# GET /api/repos/{repo_id}/files
# ═══════════════════════════════════════════════════════════════

@router.get("/api/repos/{repo_id}/files", response_model=PaginatedFilesResponse)
async def list_files(
    repo_id: str,
    folder_path: Optional[str] = Query(None),
    extension: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PaginatedFilesResponse:
    repo = await _get_user_repo(repo_id, current_user, db)
    _require_completed(repo)

    uid = repo.id
    base = select(RepoFile).where(RepoFile.repo_id == uid)

    if folder_path is not None:
        base = base.where(RepoFile.folder_path == folder_path)
    if extension is not None:
        base = base.where(RepoFile.extension == extension)

    # Count
    count_q = select(sa_func.count()).select_from(base.subquery())
    total = (await db.execute(count_q)).scalar() or 0

    # Data
    offset = (page - 1) * limit
    rows = await db.execute(
        base.order_by(RepoFile.file_path).offset(offset).limit(limit)
    )
    items = [_file_to_response(r) for r in rows.scalars().all()]

    return PaginatedFilesResponse(
        files=items,
        total=total,
        page=page,
        limit=limit,
        has_more=(page * limit) < total,
    )


# ═══════════════════════════════════════════════════════════════
# GET /api/repos/{repo_id}/files/{file_id}
# ═══════════════════════════════════════════════════════════════

@router.get("/api/repos/{repo_id}/files/{file_id}", response_model=FileDetailResponse)
async def get_file_detail(
    repo_id: str,
    file_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> FileDetailResponse:
    repo = await _get_user_repo(repo_id, current_user, db)
    _require_completed(repo)

    try:
        fid = UUID(file_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail="Invalid file id") from e

    result = await db.execute(
        select(RepoFile).where(RepoFile.id == fid, RepoFile.repo_id == repo.id)
    )
    file_obj = result.scalar_one_or_none()
    if not file_obj:
        raise HTTPException(status_code=404, detail="File not found")

    nodes_result = await db.execute(
        select(Node)
        .where(Node.file_id == fid)
        .order_by(Node.start_line)
    )
    nodes = [_node_to_response(n, include_code=True) for n in nodes_result.scalars().all()]

    return FileDetailResponse(
        file=_file_to_response(file_obj, include_preview=True),
        nodes=nodes,
    )


# ═══════════════════════════════════════════════════════════════
# GET /api/repos/{repo_id}/nodes
# ═══════════════════════════════════════════════════════════════

@router.get("/api/repos/{repo_id}/nodes", response_model=PaginatedNodesResponse)
async def list_nodes(
    repo_id: str,
    node_type: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    file_path: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PaginatedNodesResponse:
    repo = await _get_user_repo(repo_id, current_user, db)
    _require_completed(repo)

    uid = repo.id
    base = select(Node).where(Node.repo_id == uid)

    if node_type:
        base = base.where(Node.node_type == node_type)

    if file_path:
        base = base.join(RepoFile, Node.file_id == RepoFile.id).where(
            RepoFile.file_path == file_path
        )

    if search:
        # Use ILIKE for broad matching (trigram similarity optional, needs extension)
        pattern = f"%{search}%"
        base = base.where(Node.name.ilike(pattern))

    # Count
    count_q = select(sa_func.count()).select_from(base.subquery())
    total = (await db.execute(count_q)).scalar() or 0

    # Order — if searching, order by name relevance (exact match first)
    if search:
        ordering = case(
            (Node.name.ilike(search), 0),
            (Node.name.ilike(f"{search}%"), 1),
            else_=2,
        )
        base = base.order_by(ordering, Node.name)
    else:
        base = base.order_by(Node.name)

    offset = (page - 1) * limit
    rows = await db.execute(base.offset(offset).limit(limit))
    items = [_node_to_response(n) for n in rows.scalars().all()]

    return PaginatedNodesResponse(
        nodes=items,
        total=total,
        page=page,
        limit=limit,
        has_more=(page * limit) < total,
    )


# ═══════════════════════════════════════════════════════════════
# GET /api/repos/{repo_id}/nodes/{node_id}
# ═══════════════════════════════════════════════════════════════

@router.get("/api/repos/{repo_id}/nodes/{node_id}", response_model=NodeDetailResponse)
async def get_node_detail(
    repo_id: str,
    node_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> NodeDetailResponse:
    repo = await _get_user_repo(repo_id, current_user, db)
    _require_completed(repo)

    try:
        nid = UUID(node_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail="Invalid node id") from e

    result = await db.execute(
        select(Node).where(Node.id == nid, Node.repo_id == repo.id)
    )
    node_obj = result.scalar_one_or_none()
    if not node_obj:
        raise HTTPException(status_code=404, detail="Node not found")

    # Load file
    file_resp: FileResponse | None = None
    if node_obj.file_id:
        fr = await db.execute(select(RepoFile).where(RepoFile.id == node_obj.file_id))
        file_obj = fr.scalar_one_or_none()
        if file_obj:
            file_resp = _file_to_response(file_obj, include_preview=True)

    # Outgoing edges → calls
    out_result = await db.execute(
        select(Edge, Node)
        .join(Node, Edge.to_node_id == Node.id)
        .where(Edge.from_node_id == nid)
    )
    calls: list[NodeRelation] = []
    for edge, target in out_result.all():
        fp = ""
        if target.file_id:
            fp_r = await db.execute(select(RepoFile.file_path).where(RepoFile.id == target.file_id))
            fp = fp_r.scalar() or ""
        calls.append(NodeRelation(
            node_id=str(target.id),
            name=target.name,
            type=target.node_type,
            file_path=fp,
        ))

    # Incoming edges → called_by
    in_result = await db.execute(
        select(Edge, Node)
        .join(Node, Edge.from_node_id == Node.id)
        .where(Edge.to_node_id == nid)
    )
    called_by: list[NodeRelation] = []
    for edge, source in in_result.all():
        fp = ""
        if source.file_id:
            fp_r = await db.execute(select(RepoFile.file_path).where(RepoFile.id == source.file_id))
            fp = fp_r.scalar() or ""
        called_by.append(NodeRelation(
            node_id=str(source.id),
            name=source.name,
            type=source.node_type,
            file_path=fp,
        ))

    return NodeDetailResponse(
        node=_node_to_response(node_obj, include_code=True),
        file=file_resp,
        calls=calls,
        called_by=called_by,
    )


# ═══════════════════════════════════════════════════════════════
# GET /api/repos/{repo_id}/stats
# ═══════════════════════════════════════════════════════════════

@router.get("/api/repos/{repo_id}/stats", response_model=RepoStatsResponse)
async def get_repo_stats(
    repo_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    repo = await _get_user_repo(repo_id, current_user, db)
    _require_completed(repo)

    uid = repo.id

    # 1. Count nodes grouped by type
    nt_result = await db.execute(
        select(Node.node_type, sa_func.count())
        .where(Node.repo_id == uid)
        .group_by(Node.node_type)
    )
    node_types = {row[0]: row[1] for row in nt_result.all()}

    # 2. Count files grouped by extension
    ext_result = await db.execute(
        select(RepoFile.extension, sa_func.count())
        .where(RepoFile.repo_id == uid, RepoFile.extension.isnot(None))
        .group_by(RepoFile.extension)
    )
    extensions = {row[0]: row[1] for row in ext_result.all()}

    # 3. Count files grouped by language
    lang_result = await db.execute(
        select(RepoFile.language, sa_func.count())
        .where(RepoFile.repo_id == uid, RepoFile.language.isnot(None))
        .group_by(RepoFile.language)
    )
    languages = {row[0]: row[1] for row in lang_result.all()}

    # 4. Top 10 files by line_count
    top_files_result = await db.execute(
        select(RepoFile)
        .where(RepoFile.repo_id == uid)
        .order_by(RepoFile.line_count.desc())
        .limit(10)
    )
    top_files = [_file_to_response(f) for f in top_files_result.scalars().all()]

    # 5. Top 10 nodes by complexity_score
    top_nodes_result = await db.execute(
        select(Node)
        .where(Node.repo_id == uid)
        .order_by(Node.complexity_score.desc())
        .limit(10)
    )
    top_nodes = [_node_to_response(n) for n in top_nodes_result.scalars().all()]

    # 6. Total edges
    edge_count = (await db.execute(
        select(sa_func.count()).where(Edge.repo_id == uid)
    )).scalar() or 0

    # 7. API routes count
    api_route_count = (await db.execute(
        select(sa_func.count())
        .where(Node.repo_id == uid, Node.node_type == "api_route")
    )).scalar() or 0

    data = RepoStatsResponse(
        node_types=node_types,
        extensions=extensions,
        languages=languages,
        top_files_by_size=top_files,
        top_complex_nodes=top_nodes,
        total_edges=edge_count,
        total_api_routes=api_route_count,
    )

    return JSONResponse(
        content=data.model_dump(),
        headers={"Cache-Control": "max-age=60"},
    )


# ═══════════════════════════════════════════════════════════════
# GET /api/repos/{repo_id}/api-routes
# ═══════════════════════════════════════════════════════════════

@router.get("/api/repos/{repo_id}/api-routes", response_model=ApiRoutesResponse)
async def get_api_routes(
    repo_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ApiRoutesResponse:
    repo = await _get_user_repo(repo_id, current_user, db)
    _require_completed(repo)

    result = await db.execute(
        select(Node)
        .where(Node.repo_id == repo.id, Node.node_type == "api_route")
        .order_by(Node.route_path)
    )
    routes = [_node_to_response(n, include_code=True) for n in result.scalars().all()]

    return ApiRoutesResponse(routes=routes, total=len(routes))


# ═══════════════════════════════════════════════════════════════
# POST /api/repos/{repo_id}/nodes/{node_id}/summarize  (Task 3)
# ═══════════════════════════════════════════════════════════════

@router.post(
    "/api/repos/{repo_id}/nodes/{node_id}/summarize",
    response_model=NodeSummaryResponse,
)
async def summarize_node(
    repo_id: str,
    node_id: str,
    force: bool = Query(False),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> NodeSummaryResponse:
    repo = await _get_user_repo(repo_id, current_user, db)

    try:
        nid = UUID(node_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail="Invalid node id") from e

    result = await db.execute(
        select(Node).where(Node.id == nid, Node.repo_id == repo.id)
    )
    node_obj = result.scalar_one_or_none()
    if not node_obj:
        raise HTTPException(status_code=404, detail="Node not found")

    # Return cached summary unless forced
    if node_obj.summary and not force:
        return NodeSummaryResponse(
            node_id=str(node_obj.id),
            summary=node_obj.summary,
            tags=node_obj.tags or [],
        )

    summary, tags = await generate_node_summary(node_obj, repo.name)

    node_obj.summary = summary
    node_obj.tags = tags
    db.add(node_obj)
    await db.flush()

    return NodeSummaryResponse(
        node_id=str(node_obj.id),
        summary=summary,
        tags=tags,
    )


# ═══════════════════════════════════════════════════════════════
# POST /api/repos/{repo_id}/summarize-all  (Task 4)
# ═══════════════════════════════════════════════════════════════

async def _batch_summarize(repo_id: UUID, repo_name: str) -> None:
    """Background task — summarize all unsummarized nodes."""
    from app.database import async_session_factory

    async with async_session_factory() as session:
        try:
            result = await session.execute(
                select(Node)
                .where(Node.repo_id == repo_id, Node.summary.is_(None))
                .limit(50)
            )
            nodes = list(result.scalars().all())

            for node in nodes:
                try:
                    summary, tags = await generate_node_summary(node, repo_name)
                    node.summary = summary
                    node.tags = tags
                    session.add(node)
                    await session.flush()
                except Exception:
                    logger.exception("Batch summarize failed for node %s", node.id)
                await asyncio.sleep(0.5)  # Respect Groq rate limits

            await session.commit()
            logger.info("Batch summarization completed for repo %s — %d nodes", repo_id, len(nodes))
        except Exception:
            await session.rollback()
            logger.exception("Batch summarization failed for repo %s", repo_id)


@router.post("/api/repos/{repo_id}/summarize-all", response_model=BatchSummarizeResponse)
async def summarize_all_nodes(
    repo_id: str,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> BatchSummarizeResponse:
    repo = await _get_user_repo(repo_id, current_user, db)

    count_result = await db.execute(
        select(sa_func.count())
        .where(Node.repo_id == repo.id, Node.summary.is_(None))
    )
    count = count_result.scalar() or 0

    if count == 0:
        return BatchSummarizeResponse(
            message="All nodes already have summaries",
            nodes_to_process=0,
        )

    background_tasks.add_task(_batch_summarize, repo.id, repo.name)

    return BatchSummarizeResponse(
        message="Summarization started",
        nodes_to_process=min(count, 50),
    )
