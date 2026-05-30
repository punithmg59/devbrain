import asyncio
import logging
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, text, or_, case
from app.database import get_db
from app.utils.auth import get_current_user
from app.utils.groq_client import generate_node_summary
from app.models import Repo, RepoFile, Node, Edge, FolderTree
from app.schemas.repo_detail import (
    FolderResponse,
    FileResponse,
    NodeResponse,
    EdgeResponse,
    FileTreeItem,
    PaginatedFiles,
    PaginatedNodes,
    FileWithNodes,
    NodeWithRelations,
    RepoStats,
    NodeSummaryRequest,
    NodeSummaryResponse,
    ApiRoutesResponse,
    BatchSummarizeResponse,
)

logger = logging.getLogger(__name__)
router = APIRouter(tags=["repo-detail"])

# ── Helper function ───────────────────────────

async def verify_repo_ownership(
    repo_id: str,
    user_id: str,
    db: AsyncSession
) -> Repo:
    from uuid import UUID
    try:
        rid = UUID(repo_id) if isinstance(repo_id, str) else repo_id
        uid = UUID(user_id) if isinstance(user_id, str) else user_id
    except ValueError:
        raise HTTPException(status_code=404, detail="Repo not found")

    result = await db.execute(
        select(Repo).where(
            Repo.id == rid,
            Repo.user_id == uid
        )
    )
    repo = result.scalar_one_or_none()
    if not repo:
        raise HTTPException(status_code=404, detail="Repo not found")
    return repo

# ── GET /api/repos/{repo_id}/tree ─────────────

@router.get("/api/repos/{repo_id}/tree", response_model=List[FileTreeItem])
async def get_file_tree(
    repo_id: str,
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    repo = await verify_repo_ownership(repo_id, str(current_user.id), db)
    
    if repo.analysis_status != "completed":
        raise HTTPException(
            status_code=400,
            detail="Analysis not complete yet"
        )
        
    # 3. Load ALL folders in ONE query:
    folders_result = await db.execute(
        select(FolderTree)
        .where(FolderTree.repo_id == repo.id)
        .order_by(FolderTree.folder_path)
    )
    folders = folders_result.scalars().all()

    # 4. Load ALL files in ONE query:
    files_result = await db.execute(
        select(
            RepoFile.id,
            RepoFile.file_path,
            RepoFile.file_name,
            RepoFile.extension,
            RepoFile.language,
            RepoFile.folder_path,
            RepoFile.depth,
            RepoFile.line_count,
            RepoFile.size_bytes,
            RepoFile.importance_score
        )
        .where(RepoFile.repo_id == repo.id)
        .order_by(RepoFile.file_path)
    )
    files = files_result.all()

    # 5. Build tree in Python (not in SQL)
    path_to_item = {}
    
    # Instantiate folders
    for f in folders:
        item = FileTreeItem(
            id=str(f.id),
            name=f.folder_name,
            path=f.folder_path,
            type="folder",
            depth=f.depth,
            children=[],
            file_count=f.file_count,
            function_count=f.function_count
        )
        path_to_item[f.folder_path] = item

    root_items = []
    
    def is_root_path(p: Optional[str]) -> bool:
        return not p or p in ("", ".", None)

    # Populate folder hierarchy
    for f in folders:
        item = path_to_item[f.folder_path]
        parent_path = f.parent_path
        
        if is_root_path(parent_path) or parent_path not in path_to_item:
            root_items.append(item)
        else:
            path_to_item[parent_path].children.append(item)

    # Populate files into parent folders
    for file_row in files:
        fid, file_path, file_name, extension, language, folder_path, depth, line_count, size_bytes, importance_score = file_row
        item = FileTreeItem(
            id=str(fid),
            name=file_name,
            path=file_path,
            type="file",
            depth=depth,
            children=[],
            extension=extension,
            language=language,
            line_count=line_count
        )
        
        if is_root_path(folder_path) or folder_path not in path_to_item:
            root_items.append(item)
        else:
            path_to_item[folder_path].children.append(item)

    # Sort each level: folders first, then files, alphabetically (case-insensitive)
    def sort_tree_item(tree_item: FileTreeItem):
        tree_item.children.sort(key=lambda x: (0 if x.type == "folder" else 1, x.name.lower()))
        for child in tree_item.children:
            sort_tree_item(child)

    root_items.sort(key=lambda x: (0 if x.type == "folder" else 1, x.name.lower()))
    for root in root_items:
        sort_tree_item(root)

    return root_items

# ── GET /api/repos/{repo_id}/files ────────────

@router.get("/api/repos/{repo_id}/files", response_model=PaginatedFiles)
async def get_files(
    repo_id: str,
    folder_path: Optional[str] = Query(None),
    extension: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100),
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    repo = await verify_repo_ownership(repo_id, str(current_user.id), db)
    
    base_query = select(RepoFile).where(RepoFile.repo_id == repo.id)
    if folder_path is not None:
        base_query = base_query.where(RepoFile.folder_path == folder_path)
    if extension is not None:
        base_query = base_query.where(RepoFile.extension == extension)

    # Count total
    count_query = select(func.count()).select_from(base_query.subquery())
    total = (await db.execute(count_query)).scalar() or 0
    
    # Offset/Limit
    offset = (page - 1) * limit
    data_query = base_query.order_by(RepoFile.file_path).offset(offset).limit(limit)
    result = await db.execute(data_query)
    db_files = result.scalars().all()
    
    files_list = [
        FileResponse(
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
            content_preview=f.content_preview,
            importance_score=f.importance_score
        )
        for f in db_files
    ]
    
    return PaginatedFiles(
        files=files_list,
        total=total,
        page=page,
        limit=limit,
        has_more=(page * limit) < total
    )

# ── GET /api/repos/{repo_id}/files/{file_id} ──

@router.get("/api/repos/{repo_id}/files/{file_id}", response_model=FileWithNodes)
async def get_file_detail(
    repo_id: str,
    file_id: str,
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    repo = await verify_repo_ownership(repo_id, str(current_user.id), db)
    
    from uuid import UUID
    try:
        fid = UUID(file_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="File not found")

    file_result = await db.execute(
        select(RepoFile).where(RepoFile.id == fid, RepoFile.repo_id == repo.id)
    )
    file_obj = file_result.scalar_one_or_none()
    if not file_obj:
        raise HTTPException(status_code=404, detail="File not found")

    nodes_result = await db.execute(
        select(Node).where(Node.file_id == fid).order_by(Node.start_line)
    )
    nodes = nodes_result.scalars().all()

    return FileWithNodes(
        file=FileResponse.model_validate(file_obj),
        nodes=[NodeResponse.model_validate(n) for n in nodes]
    )

# ── GET /api/repos/{repo_id}/nodes ────────────

@router.get("/api/repos/{repo_id}/nodes", response_model=PaginatedNodes)
async def get_nodes(
    repo_id: str,
    node_type: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    file_path: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100),
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    repo = await verify_repo_ownership(repo_id, str(current_user.id), db)
    
    from sqlalchemy.orm import defer
    base_query = select(Node).where(Node.repo_id == repo.id).options(defer(Node.raw_code))

    if search:
        pattern = f"%{search}%"
        # Combine ILIKE and pg_trgm similarity fallback
        similarity_clause = func.similarity(Node.name, search) > 0.2
        base_query = base_query.where(
            or_(
                Node.name.ilike(pattern),
                similarity_clause
            )
        )

    if node_type:
        base_query = base_query.where(Node.node_type == node_type)

    if file_path:
        base_query = base_query.join(RepoFile, Node.file_id == RepoFile.id).where(
            RepoFile.file_path == file_path
        )

    # Count total
    count_query = select(func.count()).select_from(base_query.subquery())
    total = (await db.execute(count_query)).scalar() or 0

    # Apply pagination
    offset = (page - 1) * limit
    if search:
        ordering = case(
            (Node.name.ilike(search), 0),
            (Node.name.ilike(f"{search}%"), 1),
            else_=2
        )
        data_query = base_query.order_by(ordering, Node.name).offset(offset).limit(limit)
    else:
        data_query = base_query.order_by(Node.name).offset(offset).limit(limit)

    result = await db.execute(data_query)
    nodes = result.scalars().all()

    return PaginatedNodes(
        nodes=[NodeResponse.model_validate(n) for n in nodes],
        total=total,
        page=page,
        limit=limit,
        has_more=(page * limit) < total
    )

# ── GET /api/repos/{repo_id}/nodes/{node_id} ──

@router.get("/api/repos/{repo_id}/nodes/{node_id}", response_model=NodeWithRelations)
async def get_node_detail(
    repo_id: str,
    node_id: str,
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    repo = await verify_repo_ownership(repo_id, str(current_user.id), db)
    
    from uuid import UUID
    try:
        nid = UUID(node_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Node not found")

    node_result = await db.execute(
        select(Node).where(Node.id == nid, Node.repo_id == repo.id)
    )
    node_obj = node_result.scalar_one_or_none()
    if not node_obj:
        raise HTTPException(status_code=404, detail="Node not found")

    file_resp = None
    if node_obj.file_id:
        file_result = await db.execute(
            select(RepoFile).where(RepoFile.id == node_obj.file_id)
        )
        file_obj = file_result.scalar_one_or_none()
        if file_obj:
            file_resp = FileResponse.model_validate(file_obj)

    # Outgoing edges with target node details (limit 20)
    outgoing_result = await db.execute(
        select(
            Edge.id,
            Edge.to_node_id,
            Node.name,
            Node.node_type,
            Node.full_path
        )
        .join(Node, Edge.to_node_id == Node.id)
        .where(Edge.from_node_id == nid)
        .limit(20)
    )
    calls = [
        {
            "edge_id": str(row[0]),
            "node_id": str(row[1]),
            "name": row[2],
            "type": row[3],
            "full_path": row[4]
        }
        for row in outgoing_result.all()
    ]

    # Incoming edges with source node details (limit 20)
    incoming_result = await db.execute(
        select(
            Edge.id,
            Edge.from_node_id,
            Node.name,
            Node.node_type,
            Node.full_path
        )
        .join(Node, Edge.from_node_id == Node.id)
        .where(Edge.to_node_id == nid)
        .limit(20)
    )
    called_by = [
        {
            "edge_id": str(row[0]),
            "node_id": str(row[1]),
            "name": row[2],
            "type": row[3],
            "full_path": row[4]
        }
        for row in incoming_result.all()
    ]

    return NodeWithRelations(
        node=NodeResponse.model_validate(node_obj),
        file=file_resp,
        calls=calls,
        called_by=called_by
    )

# ── GET /api/repos/{repo_id}/stats ────────────

@router.get("/api/repos/{repo_id}/stats", response_model=RepoStats)
async def get_repo_stats(
    repo_id: str,
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    repo = await verify_repo_ownership(repo_id, str(current_user.id), db)
    
    # 1. Node types count
    node_types_res = await db.execute(
        select(Node.node_type, func.count(Node.id))
        .where(Node.repo_id == repo.id)
        .group_by(Node.node_type)
    )
    node_types = {row[0]: row[1] for row in node_types_res.all()}

    # 2. Extensions count
    extensions_res = await db.execute(
        select(RepoFile.extension, func.count(RepoFile.id))
        .where(RepoFile.repo_id == repo.id, RepoFile.extension.isnot(None))
        .group_by(RepoFile.extension)
        .order_by(func.count(RepoFile.id).desc())
    )
    extensions = {row[0]: row[1] for row in extensions_res.all()}

    # 3. Languages count
    languages_res = await db.execute(
        select(RepoFile.language, func.count(RepoFile.id))
        .where(RepoFile.repo_id == repo.id, RepoFile.language.isnot(None))
        .group_by(RepoFile.language)
    )
    languages = {row[0]: row[1] for row in languages_res.all()}

    # 4. Top 10 files by line_count
    top_files_res = await db.execute(
        select(RepoFile)
        .where(RepoFile.repo_id == repo.id)
        .order_by(RepoFile.line_count.desc())
        .limit(10)
    )
    top_files = [FileResponse.model_validate(f) for f in top_files_res.scalars().all()]

    # 5. Top 10 nodes by complexity_score
    top_nodes_res = await db.execute(
        select(Node)
        .where(Node.repo_id == repo.id)
        .order_by(Node.complexity_score.desc())
        .limit(10)
    )
    top_nodes = [NodeResponse.model_validate(n) for n in top_nodes_res.scalars().all()]

    # 6. Total edges count
    edges_count_res = await db.execute(
        select(func.count(Edge.id)).where(Edge.repo_id == repo.id)
    )
    total_edges = edges_count_res.scalar() or 0

    # 7. API routes count
    api_count_res = await db.execute(
        select(func.count(Node.id)).where(Node.repo_id == repo.id, Node.node_type == 'api_route')
    )
    total_api_routes = api_count_res.scalar() or 0

    return RepoStats(
        node_types=node_types,
        extensions=extensions,
        languages=languages,
        top_files_by_size=top_files,
        top_complex_nodes=top_nodes,
        total_edges=total_edges,
        total_api_routes=total_api_routes
    )

# ── GET /api/repos/{repo_id}/api-routes ───────

@router.get("/api/repos/{repo_id}/api-routes", response_model=ApiRoutesResponse)
async def get_api_routes(
    repo_id: str,
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    repo = await verify_repo_ownership(repo_id, str(current_user.id), db)
    
    result = await db.execute(
        select(Node)
        .where(Node.repo_id == repo.id, Node.node_type == 'api_route')
        .order_by(Node.route_path, Node.http_method)
    )
    nodes = result.scalars().all()

    return ApiRoutesResponse(
        routes=[NodeResponse.model_validate(n) for n in nodes],
        total=len(nodes)
    )

# ── POST /api/repos/{repo_id}/nodes/{node_id}/summarize ──

@router.post("/api/repos/{repo_id}/nodes/{node_id}/summarize", response_model=NodeSummaryResponse)
async def summarize_node(
    repo_id: str,
    node_id: str,
    request: NodeSummaryRequest,
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    repo = await verify_repo_ownership(repo_id, str(current_user.id), db)
    
    from uuid import UUID
    try:
        nid = UUID(node_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Node not found")

    node_result = await db.execute(
        select(Node).where(Node.id == nid, Node.repo_id == repo.id)
    )
    node = node_result.scalar_one_or_none()
    if not node:
        raise HTTPException(status_code=404, detail="Node not found")

    if node.summary and not request.force:
        return NodeSummaryResponse(
            node_id=str(node.id),
            summary=node.summary,
            tags=node.tags or []
        )

    summary, tags = await generate_node_summary(
        node_name=node.name,
        node_type=node.node_type,
        full_path=node.full_path,
        signature=node.signature,
        raw_code=node.raw_code,
        repo_name=repo.name
    )

    node.summary = summary
    node.tags = tags
    await db.commit()

    return NodeSummaryResponse(
        node_id=str(node.id),
        summary=summary,
        tags=tags
    )

# ── POST /api/repos/{repo_id}/summarize-all ───

@router.post("/api/repos/{repo_id}/summarize-all", response_model=BatchSummarizeResponse)
async def summarize_all_nodes(
    repo_id: str,
    background_tasks: BackgroundTasks,
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    repo = await verify_repo_ownership(repo_id, str(current_user.id), db)
    
    count_res = await db.execute(
        select(func.count(Node.id))
        .where(Node.repo_id == repo.id, Node.summary.is_(None))
    )
    count = count_res.scalar() or 0

    if count > 0:
        background_tasks.add_task(
            process_all_summaries,
            repo_id=str(repo.id),
            user_id=str(current_user.id)
        )

    return BatchSummarizeResponse(
        message="Summarization started" if count > 0 else "All nodes already summarized",
        nodes_to_process=count
    )

# ── Background task function ──────────────────

async def process_all_summaries(repo_id: str, user_id: str):
    from app.database import async_session_factory
    from uuid import UUID

    rid = UUID(repo_id)
    uid = UUID(user_id)

    async with async_session_factory() as session:
        try:
            repo_res = await session.execute(
                select(Repo).where(Repo.id == rid, Repo.user_id == uid)
            )
            repo = repo_res.scalar_one_or_none()
            if not repo:
                logger.error(f"Background task: Repo {repo_id} not found for user {user_id}")
                return

            repo_name = repo.name

            nodes_res = await session.execute(
                select(Node)
                .where(Node.repo_id == rid, Node.summary.is_(None))
                .limit(50)
            )
            nodes = nodes_res.scalars().all()

            logger.info(f"Starting batch summarization of {len(nodes)} nodes for repo {repo_name}")

            for node in nodes:
                try:
                    summary, tags = await generate_node_summary(
                        node_name=node.name,
                        node_type=node.node_type,
                        full_path=node.full_path,
                        signature=node.signature,
                        raw_code=node.raw_code,
                        repo_name=repo_name
                    )
                    node.summary = summary
                    node.tags = tags
                    session.add(node)
                    await session.commit()
                except Exception as inner_e:
                    logger.error(f"Error summarizing node {node.id}: {inner_e}")

                await asyncio.sleep(0.5)

            logger.info(f"Completed batch summarization for repo {repo_name}")
        except Exception as e:
            logger.error(f"Failed batch summarization background task: {e}")
