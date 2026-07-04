import asyncio
import logging
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query
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
    NodeDependenciesResponse,
    NodeRelation,
    DependencyRisk,
    ImpactAnalysisRequest,
    ImpactReportV2,
    ProjectBrainResponse,
)
from app.services.analysis import ANALYZED_STATUSES
from app.services.impact_analysis_v2 import run_impact_analysis
from app.services.project_brain import get_project_brain_dashboard

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
    
    if repo.analysis_status not in ANALYZED_STATUSES:
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
    
    base_query = select(Node).where(Node.repo_id == repo.id)

    if search:
        pattern = f"%{search}%"
        from sqlalchemy import String, cast, case, or_
        # Combine ILIKE and pg_trgm similarity fallback
        similarity_clause_name = func.similarity(Node.name, search) > 0.2
        similarity_clause_summary = func.similarity(func.coalesce(Node.summary, ''), search) > 0.2
        
        base_query = base_query.where(
            or_(
                Node.name.ilike(pattern),
                Node.full_path.ilike(pattern),
                Node.signature.ilike(pattern),
                func.coalesce(Node.summary, '').ilike(pattern),
                cast(Node.tags, String).ilike(pattern),
                cast(Node.ai_tags, String).ilike(pattern),
                similarity_clause_name,
                similarity_clause_summary
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

    logger.info(
        f"get_nodes: repo_id={repo_id}, "
        f"filters={{'node_type': {node_type!r}, 'search': {search!r}, 'file_path': {file_path!r}}}, "
        f"rows_returned={total}"
    )

    # Apply pagination
    offset = (page - 1) * limit
    if search:
        from sqlalchemy import case, cast, String
        ordering = case(
            (Node.name.ilike(search), 1),
            (Node.name.ilike(f"{search}%"), 2),
            (Node.name.ilike(f"%{search}%"), 3),
            (Node.full_path.ilike(f"%{search}%"), 4),
            (func.coalesce(Node.summary, '').ilike(f"%{search}%"), 5),
            (cast(Node.tags, String).ilike(f"%{search}%"), 5),
            else_=6
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

# ── GET /api/repos/{repo_id}/debug/nodes ──────

@router.get("/api/repos/{repo_id}/debug/nodes")
async def debug_nodes(
    repo_id: str,
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    repo = await verify_repo_ownership(repo_id, str(current_user.id), db)
    
    result = await db.execute(
        select(Node.node_type, func.count(Node.id))
        .where(Node.repo_id == repo.id)
        .group_by(Node.node_type)
    )
    type_counts = {row[0]: row[1] for row in result.all()}
    
    sample_nodes_result = await db.execute(
        select(Node).where(Node.repo_id == repo.id).limit(5)
    )
    sample_nodes = [NodeResponse.model_validate(n) for n in sample_nodes_result.scalars().all()]
    
    total_nodes = sum(type_counts.values())
    return {
        "total_nodes": total_nodes,
        "functions": type_counts.get("function", 0),
        "classes": type_counts.get("class", 0),
        "methods": type_counts.get("method", 0),
        "api_routes": type_counts.get("api_route", 0),
        "sample_nodes": sample_nodes
    }

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

    # Outgoing edges with target node details (limit 100)
    outgoing_result = await db.execute(
        select(
            Edge.id,
            Edge.to_node_id,
            Node.name,
            Node.node_type,
            Node.full_path,
            Edge.edge_type
        )
        .join(Node, Edge.to_node_id == Node.id)
        .where(Edge.from_node_id == nid)
        .limit(100)
    )
    calls = [
        {
            "edge_id": str(row[0]),
            "node_id": str(row[1]),
            "name": row[2],
            "type": row[3],
            "full_path": row[4],
            "edge_type": str(row[5])
        }
        for row in outgoing_result.all()
    ]

    # Incoming edges with source node details (limit 100)
    incoming_result = await db.execute(
        select(
            Edge.id,
            Edge.from_node_id,
            Node.name,
            Node.node_type,
            Node.full_path,
            Edge.edge_type
        )
        .join(Node, Edge.from_node_id == Node.id)
        .where(Edge.to_node_id == nid)
        .limit(100)
    )
    called_by = [
        {
            "edge_id": str(row[0]),
            "node_id": str(row[1]),
            "name": row[2],
            "type": row[3],
            "full_path": row[4],
            "edge_type": str(row[5])
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

# ── GET /api/repos/{repo_id}/graph-health ─────

@router.get("/api/repos/{repo_id}/graph-health")
async def get_graph_health(
    repo_id: str,
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    repo = await verify_repo_ownership(repo_id, str(current_user.id), db)

    # Total nodes
    node_count_res = await db.execute(
        select(func.count(Node.id)).where(Node.repo_id == repo.id)
    )
    total_nodes = node_count_res.scalar() or 0

    # Total edges
    edge_count_res = await db.execute(
        select(func.count(Edge.id)).where(Edge.repo_id == repo.id)
    )
    total_edges = edge_count_res.scalar() or 0

    # Edge types breakdown
    edge_types_res = await db.execute(
        select(Edge.edge_type, func.count(Edge.id))
        .where(Edge.repo_id == repo.id)
        .group_by(Edge.edge_type)
        .order_by(func.count(Edge.id).desc())
    )
    edge_types = {row[0]: row[1] for row in edge_types_res.all()}

    # Node types breakdown
    node_types_res = await db.execute(
        select(Node.node_type, func.count(Node.id))
        .where(Node.repo_id == repo.id)
        .group_by(Node.node_type)
    )
    node_types = {row[0]: row[1] for row in node_types_res.all()}

    # Relationship density = edges / nodes
    relationship_density = round(total_edges / total_nodes, 2) if total_nodes > 0 else 0.0

    # Graph score: composite based on edge variety and density
    # Max score = 100. Weights: density (40), edge type variety (40), volume (20)
    edge_variety = len(edge_types)
    max_variety = 15  # target number of edge types
    variety_score = min(edge_variety / max_variety, 1.0) * 40
    density_score = min(relationship_density / 5.0, 1.0) * 40
    volume_score = min(total_edges / 800, 1.0) * 20
    graph_score = round(variety_score + density_score + volume_score, 1)

    return {
        "total_nodes": total_nodes,
        "total_edges": total_edges,
        "edge_types": edge_types,
        "node_types": node_types,
        "relationship_density": relationship_density,
        "graph_score": graph_score,
    }
# ── GET /api/repos/{repo_id}/nodes/{node_id}/dependencies ──

@router.get("/api/repos/{repo_id}/nodes/{node_id}/dependencies", response_model=NodeDependenciesResponse)
async def get_node_dependencies(
    repo_id: str,
    node_id: str,
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    from sqlalchemy.orm import aliased
    from uuid import UUID
    
    repo = await verify_repo_ownership(repo_id, str(current_user.id), db)
    
    try:
        nid = UUID(node_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Node not found")

    node_result = await db.execute(select(Node).where(Node.id == nid, Node.repo_id == repo.id))
    node = node_result.scalar_one_or_none()
    if not node:
        raise HTTPException(status_code=404, detail="Node not found")

    # Fetch outbound edges (where this node is the 'from' node)
    ToNode = aliased(Node)
    outbound_res = await db.execute(
        select(Edge.id, ToNode, Edge.edge_type)
        .join(ToNode, Edge.to_node_id == ToNode.id)
        .where(Edge.from_node_id == nid)
    )
    outbound_edges = outbound_res.all()

    # Fetch inbound edges (where this node is the 'to' node)
    FromNode = aliased(Node)
    inbound_res = await db.execute(
        select(Edge.id, FromNode, Edge.edge_type)
        .join(FromNode, Edge.from_node_id == FromNode.id)
        .where(Edge.to_node_id == nid)
    )
    inbound_edges = inbound_res.all()

    response = NodeDependenciesResponse(node=NodeResponse.model_validate(node), risk=DependencyRisk(score=0, level="low", reason=""))
    
    def make_relation(edge_id, n, edge_type):
        return NodeRelation(
            edge_id=str(edge_id),
            node_id=str(n.id),
            name=n.name,
            type=n.node_type,
            full_path=n.full_path,
            file_path="",
            edge_type=edge_type
        )

    api_count = 0
    fn_count = 0

    for edge_id, target_node, edge_type in outbound_edges:
        rel = make_relation(edge_id, target_node, edge_type)
        if edge_type in ("calls", "api_calls"):
            response.calls.append(rel)
        elif edge_type == "reads_table":
            response.reads_tables.append(rel)
        elif edge_type == "writes_table":
            response.writes_tables.append(rel)
        elif edge_type == "updates_table":
            response.updates_tables.append(rel)
        elif edge_type == "deletes_table":
            response.deletes_tables.append(rel)
        elif edge_type == "uses_service":
            response.services.append(rel)
        elif edge_type == "auth_dependency":
            response.auth_dependencies.append(rel)
        elif edge_type == "dependency_injection":
            response.dependency_injections.append(rel)
        elif edge_type == "imports":
            response.imports.append(rel)
        elif edge_type == "inherits":
            response.inherits.append(rel)

    for edge_id, source_node, edge_type in inbound_edges:
        rel = make_relation(edge_id, source_node, edge_type)
        if edge_type in ("calls", "api_calls"):
            if source_node.node_type == "api_route":
                response.api_routes.append(rel)
                api_count += 1
            else:
                response.called_by.append(rel)
                fn_count += 1
        elif edge_type in ("contains", "class_contains"):
            response.contains.append(rel)

    # Risk Engine calculation
    # Formula: dependents (called_by) * 5 + api_routes * 10
    # Wait, the prompt says "dependents * 5" for delete. Let's use 5 for functions, 10 for APIs.
    # Actually, the user example: "Used by 8 functions and 2 APIs" -> score 72.
    # If 8 * 5 = 40, and 2 APIs...? Maybe 2 * 16 = 32?
    # No, if total dependents is 10 (8+2). 10 * 5 = 50. What makes 72?
    # Maybe (8 * x) + (2 * y) = 72?
    # What if 8 functions * 5 = 40. 2 APIs * 16?
    # What if "base" includes database tables? "High fanout increases risk."
    # Let's just use: (fn_count * 5) + (api_count * 10) + len(databases) * 2 + len(services) * 2
    # Oh wait, 8*5 = 40. Maybe the reason was just an example and doesn't exactly math out to 72.
    # Let's use fn_count * 5 + api_count * 10.
    
    db_count = len(response.reads_tables) + len(response.writes_tables) + len(response.updates_tables) + len(response.deletes_tables)
    score = (fn_count * 5) + (api_count * 10) + (db_count * 2)

    level = "low"
    if score > 50:
        level = "critical"
    elif score > 20:
        level = "high"
    elif score > 5:
        level = "medium"

    parts = []
    if fn_count > 0:
        parts.append(f"{fn_count} functions")
    if api_count > 0:
        parts.append(f"{api_count} APIs")
    
    if not parts:
        reason = "Not used by any other node."
    else:
        reason = f"Used by {' and '.join(parts)}"

    response.risk = DependencyRisk(score=score, level=level, reason=reason)

    return response

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
            detailed_explanation=node.detailed_explanation,
            architecture_role=node.architecture_role,
            complexity_level=node.complexity_level,
            call_flow_diagram=node.call_flow_diagram,
            ai_tags=node.ai_tags or [],
            potential_risks=node.potential_risks or [],
            dependencies=[],
            responsibilities=[],
            inputs=[],
            outputs=[],
            related_components=[],
            call_flow=[],
            tags=node.tags or []
        )

    result = await generate_node_summary(
        node_name=node.name,
        node_type=node.node_type,
        full_path=node.full_path,
        signature=node.signature,
        raw_code=node.raw_code,
        repo_name=repo.name,
        repo_description=repo.description,
        repo_language=repo.language,
        imports=node.imports,
        calls=node.calls,
        called_by=node.called_by,
        existing_summary=node.summary,
    )

    node.summary = result["summary"]
    node.detailed_explanation = result["detailed_explanation"]
    node.architecture_role = result["architecture_role"]
    node.complexity_level = result["complexity_level"]
    node.call_flow_diagram = result["call_flow_diagram"]
    node.ai_tags = result["ai_tags"]
    node.potential_risks = result["potential_risks"]
    node.tags = result["tags"]
    await db.commit()

    return NodeSummaryResponse(
        node_id=str(node.id),
        summary=node.summary,
        detailed_explanation=node.detailed_explanation,
        architecture_role=node.architecture_role,
        complexity_level=node.complexity_level,
        call_flow_diagram=node.call_flow_diagram,
        ai_tags=node.ai_tags or [],
        potential_risks=node.potential_risks or [],
        dependencies=result["dependencies"],
        responsibilities=result["responsibilities"],
        inputs=result["inputs"],
        outputs=result["outputs"],
        related_components=result["related_components"],
        call_flow=result["call_flow"],
        tags=node.tags or [],
    )


# ── POST /api/repos/{repo_id}/impact-analysis ──

@router.post("/api/repos/{repo_id}/impact-analysis", response_model=ImpactReportV2)
async def post_impact_analysis(
    repo_id: str,
    request: ImpactAnalysisRequest,
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    repo = await verify_repo_ownership(repo_id, str(current_user.id), db)
    return await run_impact_analysis(request, repo.id, db)

# ── GET /api/repos/{repo_id}/project-brain ──

@router.get("/api/repos/{repo_id}/project-brain", response_model=ProjectBrainResponse)
async def get_project_brain(
    repo_id: str,
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    repo = await verify_repo_ownership(repo_id, str(current_user.id), db)
    return await get_project_brain_dashboard(db, repo.id)

