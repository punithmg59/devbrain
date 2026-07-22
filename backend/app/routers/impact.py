import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select, text
from sqlalchemy.exc import DBAPIError, DisconnectionError, OperationalError
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Repo, User, ImpactAnalysis
from app.schemas.impact import (
    BlastRadiusReport,
    BlastRadiusRequest,
    CriticalPathSummary,
    ExactDependencies,
    ExactDependencyItem,
    GraphEdge,
    GraphNode,
    ImpactGraph,
    ImpactGraphResponse,
    ImpactMetricSummary,
    ImpactRequest,
    ImpactResult,
    SimpleImpactRequest,
    SimpleImpactResult,
    NodeSearchResult,
    ImpactHistoryItem,
)
from app.schemas.resolver import (
    AutocompleteResponse,
    ResolveRequest,
    ResolveResponse,
)
from app.services.analysis import ANALYZED_STATUSES
from app.services.impact_service import ImpactService
from app.services.resolver_service import SmartResolver
from app.services.impact.impact_analyzer import analyze_impact as analyze_impact_node
from app.services.impact.recommendations import generate_recommendations
from app.utils.auth import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter(tags=["impact"])
impact_service = ImpactService()
smart_resolver = SmartResolver()

VALID_DIRECTIONS = {"both", "downstream", "upstream"}


class ImpactCompareRequest(BaseModel):
    query_a: str
    query_b: str
    max_depth: int = 6
    direction: str = "both"


def _is_db_unavailable(exc: Exception) -> bool:
    if isinstance(exc, DisconnectionError):
        return True
    msg = str(exc).lower()
    if "connection" in msg and ("refused" in msg or "closed" in msg or "lost" in msg):
        return True
    orig = getattr(exc, "orig", None)
    if orig is not None:
        orig_msg = str(orig).lower()
        if "connection" in orig_msg:
            return True
    return False


async def _get_user_repo(
    repo_id: str,
    current_user: User,
    db: AsyncSession,
) -> Repo:
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


@router.post(
    "/api/repos/{repo_id}/impact/resolve",
    response_model=ResolveResponse,
)
async def resolve_query(
    repo_id: str,
    request: ResolveRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ResolveResponse:
    try:
        repo = await _get_user_repo(repo_id, current_user, db)
        if repo.analysis_status not in ANALYZED_STATUSES:
            raise HTTPException(
                status_code=400,
                detail="Repository analysis not complete",
            )
        q = request.query.strip()
        if not q:
            raise HTTPException(status_code=400, detail="Query cannot be empty")

        entities, ms = await smart_resolver.resolve(
            q,
            str(repo.id),
            db,
            user_id=str(current_user.id),
            limit=min(request.limit, 20),
        )
        primary = entities[0] if entities else None
        return ResolveResponse(
            query=q,
            resolved_entities=entities,
            primary_entity=primary,
            resolution_ms=ms,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Resolve failed: %s", e)
        raise HTTPException(status_code=500, detail="Resolution failed") from e


@router.get(
    "/api/repos/{repo_id}/impact/autocomplete",
    response_model=AutocompleteResponse,
)
async def autocomplete_impact(
    repo_id: str,
    q: str = "",
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AutocompleteResponse:
    try:
        repo = await _get_user_repo(repo_id, current_user, db)
        suggestions = await smart_resolver.autocomplete(
            q.strip(),
            str(repo.id),
            db,
            limit=12,
        )
        return AutocompleteResponse(suggestions=suggestions)
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Autocomplete failed: %s", e)
        raise HTTPException(status_code=500, detail="Autocomplete failed") from e


@router.post(
    "/api/repos/{repo_id}/impact",
    response_model=ImpactResult,
)
async def analyze_impact(
    repo_id: str,
    request: ImpactRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ImpactResult:
    try:
        repo = await _get_user_repo(repo_id, current_user, db)

        if repo.analysis_status not in ANALYZED_STATUSES:
            raise HTTPException(
                status_code=400,
                detail=(
                    "This repository has not been analyzed yet. "
                    "Run analysis from the dashboard first."
                ),
            )

        q = request.query.strip()
        if not q:
            raise HTTPException(status_code=400, detail="Query cannot be empty")
        if len(q) > 200:
            raise HTTPException(status_code=400, detail="Query too long")
        if request.max_depth < 1 or request.max_depth > 10:
            raise HTTPException(status_code=400, detail="max_depth must be 1-10")
        if request.direction not in VALID_DIRECTIONS:
            raise HTTPException(
                status_code=400,
                detail="direction must be both, downstream, or upstream",
            )

        return await impact_service.analyze(
            query=q,
            repo_id=str(repo.id),
            max_depth=request.max_depth,
            direction=request.direction,
            db=db,
            natural_language=request.natural_language,
            repo_name=repo.full_name,
            scenario=request.scenario,
        )
    except HTTPException:
        raise
    except (OperationalError, DisconnectionError, DBAPIError) as e:
        if _is_db_unavailable(e):
            logger.exception("Database unavailable during impact analysis")
            raise HTTPException(
                status_code=500,
                detail="Analysis temporarily unavailable",
            ) from e
        logger.exception("Database error during impact analysis")
        raise HTTPException(
            status_code=500,
            detail="Analysis failed. Please try again.",
        ) from e
    except Exception as e:
        logger.exception("Impact analysis failed: %s", e)
        raise HTTPException(
            status_code=500,
            detail="Analysis failed. Please try again.",
        ) from e


@router.post("/api/repos/{repo_id}/impact/compare")
async def compare_impact(
    repo_id: str,
    request: ImpactCompareRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Compare blast radius of two change targets (premium)."""
    try:
        repo = await _get_user_repo(repo_id, current_user, db)
        if repo.analysis_status not in ANALYZED_STATUSES:
            raise HTTPException(status_code=400, detail="Repository analysis not complete")

        a = await impact_service.analyze(
            query=request.query_a.strip(),
            repo_id=str(repo.id),
            max_depth=request.max_depth,
            direction=request.direction,
            db=db,
            natural_language=True,
            repo_name=repo.full_name,
        )
        b = await impact_service.analyze(
            query=request.query_b.strip(),
            repo_id=str(repo.id),
            max_depth=request.max_depth,
            direction=request.direction,
            db=db,
            natural_language=True,
            repo_name=repo.full_name,
        )
        ids_a = {n.id for n in a.impacted_nodes}
        ids_b = {n.id for n in b.impacted_nodes}
        return {
            "query_a": request.query_a,
            "query_b": request.query_b,
            "report_a": a,
            "report_b": b,
            "shared_nodes": len(ids_a & ids_b),
            "only_in_a": len(ids_a - ids_b),
            "only_in_b": len(ids_b - ids_a),
            "risk_delta": (b.risk_score_100 or 0) - (a.risk_score_100 or 0),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Impact compare failed: %s", e)
        raise HTTPException(status_code=500, detail="Compare failed. Please try again.") from e


@router.post("/api/repos/{repo_id}/impact/seed-aliases")
async def seed_resolver_aliases(
    repo_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Rebuild aliases + embeddings for an already-analyzed repo."""
    try:
        repo = await _get_user_repo(repo_id, current_user, db)
        if repo.analysis_status not in ANALYZED_STATUSES:
            raise HTTPException(status_code=400, detail="Repository analysis not complete")
        from app.services.alias_seeder import (
            index_node_embeddings,
            link_workflow_aliases_to_nodes,
            seed_aliases_for_repo,
        )

        count = await seed_aliases_for_repo(repo.id, db)
        await link_workflow_aliases_to_nodes(repo.id, db)
        emb = await index_node_embeddings(repo.id, db)
        return {"aliases_seeded": count, "embeddings_indexed": emb}
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Seed aliases failed: %s", e)
        raise HTTPException(status_code=500, detail="Seed failed") from e


@router.get("/api/repos/{repo_id}/impact/search")
async def search_nodes_for_impact(
    repo_id: str,
    q: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        repo = await _get_user_repo(repo_id, current_user, db)

        if not q or not q.strip():
            return []

        pattern = f"%{q.strip()}%"
        sql = text("""
            SELECT n.id, n.name, n.node_type,
                   COALESCE(rf.file_path, '') as file_path
            FROM nodes n
            LEFT JOIN repo_files rf ON n.file_id = rf.id
            WHERE n.repo_id = :repo_id
            AND (
                n.name ILIKE :pattern
                OR rf.file_path ILIKE :pattern
            )
            ORDER BY n.name
            LIMIT 10
        """)
        result = await db.execute(
            sql,
            {"repo_id": str(repo.id), "pattern": pattern},
        )
        rows = []
        for row in result.mappings():
            d = dict(row)
            if isinstance(d.get("id"), UUID):
                d["id"] = str(d["id"])
            rows.append(d)
        return rows
    except HTTPException:
        raise
    except (OperationalError, DisconnectionError, DBAPIError) as e:
        if _is_db_unavailable(e):
            logger.exception("Database unavailable during impact search")
            raise HTTPException(
                status_code=500,
                detail="Analysis temporarily unavailable",
            ) from e
        logger.exception("Database error during impact search")
        raise HTTPException(
            status_code=500,
            detail="Search failed. Please try again.",
        ) from e
    except Exception as e:
        logger.exception("Impact search failed: %s", e)
        raise HTTPException(
            status_code=500,
            detail="Search failed. Please try again.",
        ) from e


@router.post(
    "/api/repos/{repo_id}/impact/blast-radius",
    response_model=BlastRadiusReport,
)
async def blast_radius_report(
    repo_id: str,
    request: BlastRadiusRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> BlastRadiusReport:
    repo = await _get_user_repo(repo_id, current_user, db)
    if repo.analysis_status not in ANALYZED_STATUSES:
        raise HTTPException(status_code=400, detail="Repository analysis not complete")
    q = request.query.strip()
    if not q:
        raise HTTPException(status_code=400, detail="Query cannot be empty")
    result = await impact_service.analyze(
        query=q,
        repo_id=str(repo.id),
        max_depth=request.max_depth,
        direction=request.direction,
        db=db,
        natural_language=request.natural_language,
        repo_name=repo.full_name,
        scenario=request.scenario,
    )
    if result.blast_radius_report:
        return result.blast_radius_report
    raise HTTPException(status_code=404, detail="Could not resolve source for blast radius")


@router.get("/api/repos/{repo_id}/impact/critical-paths")
async def list_critical_paths(
    repo_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from app.services.critical_path_service import CriticalPathService

    repo = await _get_user_repo(repo_id, current_user, db)
    paths = await CriticalPathService().list_paths(repo.id, db)
    return [
        CriticalPathSummary(
            id=str(p.id),
            name=p.name,
            criticality=p.criticality,
            description=p.description,
            impacted_node_names=[n.get("name", "") for n in (p.path_nodes or [])],
        )
        for p in paths
    ]


@router.get(
    "/api/repos/{repo_id}/impact/metrics",
    response_model=list[ImpactMetricSummary],
)
async def list_impact_metrics(
    repo_id: str,
    limit: int = 50,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[ImpactMetricSummary]:
    repo = await _get_user_repo(repo_id, current_user, db)
    limit = min(max(1, limit), 200)
    sql = text("""
        SELECT im.node_id, n.name AS node_name, im.centrality_score,
               im.dependency_count, im.workflow_count, im.in_degree, im.out_degree
        FROM impact_metrics im
        JOIN nodes n ON n.id = im.node_id
        WHERE im.repo_id = :repo_id
        ORDER BY im.centrality_score DESC
        LIMIT :limit
    """)
    rows = (
        await db.execute(sql, {"repo_id": str(repo.id), "limit": limit})
    ).mappings()
    return [
        ImpactMetricSummary(
            node_id=str(r["node_id"]),
            node_name=r["node_name"],
            centrality_score=float(r["centrality_score"]),
            dependency_count=int(r["dependency_count"]),
            workflow_count=int(r["workflow_count"]),
            in_degree=int(r["in_degree"]),
            out_degree=int(r["out_degree"]),
        )
        for r in rows
    ]


@router.post("/api/repos/{repo_id}/impact/recompute")
async def recompute_impact_metrics(
    repo_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from app.services.critical_path_service import CriticalPathService
    from app.services.impact_precompute_service import ImpactPrecomputeService
    from app.services.workflow_discovery_service import WorkflowDiscoveryService

    repo = await _get_user_repo(repo_id, current_user, db)
    if repo.analysis_status not in ANALYZED_STATUSES:
        raise HTTPException(status_code=400, detail="Repository analysis not complete")
    workflows = await WorkflowDiscoveryService().discover_for_repo(repo.id, db)
    paths = await CriticalPathService().seed_for_repo(repo.id, db)
    metrics = await ImpactPrecomputeService().recompute_for_repo(repo.id, db)
    return {
        "workflows_discovered": workflows,
        "critical_paths_seeded": paths,
        "metrics_computed": metrics,
    }


# ── Impact Graph Endpoint (Exact Dependency Intelligence) ─────────────────────

@router.get(
    "/api/repos/{repo_id}/impact-graph/{node_id}",
    response_model=ImpactGraphResponse,
)
async def get_impact_graph(
    repo_id: str,
    node_id: str,
    max_depth: int = 3,
    direction: str = "both",
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Return exact dependency intelligence for a single node.

    Levels:
    - L1 (depth=1): Direct dependencies (directly calls / called by)
    - L2 (depth=2): Indirect dependencies (transitive)
    - L3 (depth>=3): Business workflow dependencies

    Also extracts:
    - database_dependencies (node_type in db/table/model)
    - api_dependencies (node_type = api_route)
    - file_dependencies (unique file paths)

    Graph-ready structure for visualization.
    Supports 100k+ files / 1M+ nodes via CTE traversal with depth limits.
    """
    repo = await _get_user_repo(repo_id, current_user, db)

    try:
        node_uuid = UUID(node_id)
        repo_uuid = UUID(repo_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail="Invalid node or repo id") from e

    # ── Fetch source node ─────────────────────────────────────────
    source_sql = text("""
        SELECT n.id, n.name, n.node_type, n.start_line, n.end_line,
               COALESCE(rf.file_path, '') as file_path
        FROM nodes n
        LEFT JOIN repo_files rf ON n.file_id = rf.id
        WHERE n.id = :node_id AND n.repo_id = :repo_id
    """)
    source_res = await db.execute(source_sql, {"node_id": node_uuid, "repo_id": repo_uuid})
    source_row = source_res.mappings().one_or_none()
    if not source_row:
        raise HTTPException(status_code=404, detail="Node not found in this repository")

    # ── Traverse downstream ───────────────────────────────────────
    downstream_sql = text("""
        WITH RECURSIVE downstream AS (
            SELECT n.id, n.name, n.node_type,
                   COALESCE(rf.file_path, '') as file_path,
                   n.start_line, n.end_line, 1 as depth,
                   'downstream' as direction, e.edge_type,
                   ARRAY[n.id::text] as visited
            FROM edges e
            JOIN nodes n ON n.id = e.to_node_id
            LEFT JOIN repo_files rf ON n.file_id = rf.id
            WHERE e.from_node_id = :node_id AND e.repo_id = :repo_id AND n.repo_id = :repo_id
            UNION ALL
            SELECT n2.id, n2.name, n2.node_type,
                   COALESCE(rf2.file_path, '') as file_path,
                   n2.start_line, n2.end_line, ds.depth + 1,
                   'downstream' as direction, e2.edge_type,
                   ds.visited || n2.id::text
            FROM downstream ds
            JOIN edges e2 ON e2.from_node_id = ds.id AND e2.repo_id = :repo_id
            JOIN nodes n2 ON n2.id = e2.to_node_id AND n2.repo_id = :repo_id
            LEFT JOIN repo_files rf2 ON n2.file_id = rf2.id
            WHERE ds.depth < :max_depth
              AND NOT n2.id::text = ANY(ds.visited)
        )
        SELECT DISTINCT ON (id) id, name, node_type, file_path, start_line, end_line, depth, direction, edge_type
        FROM downstream ORDER BY id, depth
    """)

    # ── Traverse upstream ─────────────────────────────────────────
    upstream_sql = text("""
        WITH RECURSIVE upstream AS (
            SELECT n.id, n.name, n.node_type,
                   COALESCE(rf.file_path, '') as file_path,
                   n.start_line, n.end_line, 1 as depth,
                   'upstream' as direction, e.edge_type,
                   ARRAY[n.id::text] as visited
            FROM edges e
            JOIN nodes n ON n.id = e.from_node_id
            LEFT JOIN repo_files rf ON n.file_id = rf.id
            WHERE e.to_node_id = :node_id AND e.repo_id = :repo_id AND n.repo_id = :repo_id
            UNION ALL
            SELECT n2.id, n2.name, n2.node_type,
                   COALESCE(rf2.file_path, '') as file_path,
                   n2.start_line, n2.end_line, us.depth + 1,
                   'upstream' as direction, e2.edge_type,
                   us.visited || n2.id::text
            FROM upstream us
            JOIN edges e2 ON e2.to_node_id = us.id AND e2.repo_id = :repo_id
            JOIN nodes n2 ON n2.id = e2.from_node_id AND n2.repo_id = :repo_id
            LEFT JOIN repo_files rf2 ON n2.file_id = rf2.id
            WHERE us.depth < :max_depth
              AND NOT n2.id::text = ANY(us.visited)
        )
        SELECT DISTINCT ON (id) id, name, node_type, file_path, start_line, end_line, depth, direction, edge_type
        FROM upstream ORDER BY id, depth
    """)

    params = {"node_id": node_uuid, "repo_id": repo_uuid, "max_depth": max_depth}
    all_dep_rows: list[dict] = []

    if direction in ("downstream", "both"):
        res = await db.execute(downstream_sql, params)
        all_dep_rows.extend(dict(r) for r in res.mappings())

    if direction in ("upstream", "both"):
        res = await db.execute(upstream_sql, params)
        all_dep_rows.extend(dict(r) for r in res.mappings())

    # De-duplicate by id, prefer shallower depth
    by_id: dict[str, dict] = {}
    for row in all_dep_rows:
        rid = str(row["id"])
        if rid not in by_id or row["depth"] < by_id[rid]["depth"]:
            by_id[rid] = row

    dep_nodes = list(by_id.values())
    all_ids = [str(source_row["id"])] + list(by_id.keys())

    # ── Load subgraph edges for those IDs ────────────────────────
    edges_sql = text("""
        SELECT from_node_id, to_node_id, edge_type
        FROM edges
        WHERE repo_id = :repo_id
          AND from_node_id = ANY(CAST(:ids AS uuid[]))
          AND to_node_id = ANY(CAST(:ids AS uuid[]))
    """)
    edge_res = await db.execute(edges_sql, {"repo_id": repo_uuid, "ids": all_ids})
    raw_edges = [dict(r) for r in edge_res.mappings()]

    # ── Build ExactDependencies ───────────────────────────────────
    level_1_direct: list[ExactDependencyItem] = []
    level_1_incoming: list[ExactDependencyItem] = []
    level_2_indirect: list[ExactDependencyItem] = []
    level_3_workflow: list[ExactDependencyItem] = []
    database_deps: list[ExactDependencyItem] = []
    api_deps: list[ExactDependencyItem] = []
    files: set[str] = set()

    for n in dep_nodes:
        fp = n.get("file_path") or ""
        if fp:
            files.add(fp)
        item = ExactDependencyItem(
            id=str(n["id"]),
            name=n["name"],
            node_type=n.get("node_type", "unknown"),
            file_path=fp,
            confidence=1.0,
        )
        depth = n.get("depth", 1)
        dir_ = n.get("direction", "downstream")
        if depth == 1:
            if dir_ == "downstream":
                level_1_direct.append(item)
            else:
                level_1_incoming.append(item)
        elif depth == 2:
            level_2_indirect.append(item)
        else:
            level_3_workflow.append(item)

        ntype = item.node_type.lower()
        if ntype in ("database", "table", "db", "model"):
            database_deps.append(item)
        elif ntype in ("api_route", "endpoint", "route"):
            api_deps.append(item)

    exact_deps = ExactDependencies(
        level_1_direct=level_1_direct,
        level_1_incoming=level_1_incoming,
        level_2_indirect=level_2_indirect,
        level_3_workflow=level_3_workflow,
        database_dependencies=database_deps,
        api_dependencies=api_deps,
        file_dependencies=list(files),
    )

    # ── Build Graph structure ─────────────────────────────────────
    # Assign risk tiers based on depth
    def _tier(depth: int) -> str:
        if depth == 0: return "critical"
        if depth == 1: return "high"
        if depth == 2: return "medium"
        return "low"

    graph_nodes = [
        GraphNode(
            id=str(source_row["id"]),
            name=source_row["name"],
            node_type=source_row.get("node_type", "unknown"),
            file_path=source_row.get("file_path") or "",
            risk_tier="critical",
            is_source=True,
            depth=0,
            confidence=1.0,
        )
    ] + [
        GraphNode(
            id=str(n["id"]),
            name=n["name"],
            node_type=n.get("node_type", "unknown"),
            file_path=n.get("file_path") or "",
            risk_tier=_tier(n.get("depth", 1)),
            is_source=False,
            depth=n.get("depth", 1),
            confidence=1.0,
        )
        for n in dep_nodes[:500]  # cap for safety on very large repos
    ]

    graph_edges = [
        GraphEdge(
            from_id=str(e["from_node_id"]),
            to_id=str(e["to_node_id"]),
            edge_type=e.get("edge_type") or "calls",
            confidence=1.0,
        )
        for e in raw_edges
    ]

    return ImpactGraphResponse(
        repo_id=repo_id,
        source_node_id=node_id,
        exact_dependencies=exact_deps,
        graph=ImpactGraph(nodes=graph_nodes, edges=graph_edges),
    )


# ── New simplified Impact API endpoints (Day 6) ─────────────────────────────

@router.post("/api/impact/analyze", response_model=SimpleImpactResult)
async def analyze_impact_endpoint(
    request: SimpleImpactRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Run impact analysis on a specific node by node_id.

    Steps:
        1. Verify repo exists and user has access
        2. Run impact analysis (Neo4j traversal)
        3. Generate AI recommendations
        4. Save analysis to impact_analyses table
        5. Return ImpactResult

    Cached for 1 hour per node — fast on repeated calls.
    """
    # Step 1: verify repo
    try:
        uid = UUID(request.repo_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail="Invalid repository id") from e

    repo = (await db.execute(
        select(Repo).where(Repo.id == uid, Repo.user_id == current_user.id)
    )).scalar_one_or_none()
    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found")

    # Step 2: run analysis
    try:
        result = await analyze_impact_node(request.node_id, request.repo_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        logger.exception("Impact analysis failed for node %s", request.node_id)
        raise HTTPException(status_code=500, detail="Impact analysis failed")

    # Step 3: generate AI recommendations
    recommendations = await generate_recommendations(result)
    result.recommendations = recommendations

    # Step 4: save to history
    try:
        record = ImpactAnalysis(
            repo_id=request.repo_id,
            node_id=request.node_id,
            node_name=result.node_name,
            node_type=result.node_type,
            risk_score=result.risk_score.value,
            risk_level=result.risk_score.level,
            blast_radius=result.blast_radius,
            affected_count=len(result.affected_nodes),
            effort_label=result.effort_estimate.label,
            recommendations=[r.dict() for r in recommendations],
        )
        db.add(record)
        await db.commit()
    except Exception as exc:
        logger.warning("Could not save impact history: %s", exc)
        # Non-fatal — return result even if save fails

    return result


@router.get("/api/impact/search/{repo_id}", response_model=list[NodeSearchResult])
async def search_nodes(
    repo_id: str,
    q: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Search nodes by name for the Impact page search bar.
    Returns up to 20 results ordered by blast_radius descending.
    Used as the user types to find components to analyze.
    """
    try:
        uid = UUID(repo_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail="Invalid repository id") from e

    repo = (await db.execute(
        select(Repo).where(Repo.id == uid, Repo.user_id == current_user.id)
    )).scalar_one_or_none()
    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found")

    query = """
    SELECT 
        id,
        name,
        node_type,
        full_path as file_path,
        blast_radius,
        risk_level,
        fan_in
    FROM nodes
    WHERE repo_id = :repo_id
    AND LOWER(name) LIKE LOWER(:search)
    ORDER BY blast_radius DESC, fan_in DESC
    LIMIT 20
    """
    try:
        result = await db.execute(text(query), {"repo_id": repo_id, "search": f"%{q}%"})
        rows = result.fetchall()
    except Exception as exc:
        logger.error("PostgreSQL search failed: %s", exc)
        raise HTTPException(status_code=500, detail="Search failed")

    return [
        NodeSearchResult(
            id=str(r.id),
            name=r.name,
            node_type=r.node_type,
            file_path=r.file_path,
            blast_radius=r.blast_radius or 0,
            risk_level=r.risk_level or "low",
            fan_in=r.fan_in or 0,
        )
        for r in rows
    ]


@router.get("/api/impact/top/{repo_id}", response_model=list[NodeSearchResult])
async def get_top_impact_nodes(
    repo_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Return top 20 nodes by blast_radius.
    Shown on Impact page initial load.
    Answers: which components are highest risk right now?
    """
    try:
        uid = UUID(repo_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail="Invalid repository id") from e

    repo = (await db.execute(
        select(Repo).where(Repo.id == uid, Repo.user_id == current_user.id)
    )).scalar_one_or_none()
    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found")

    query = """
    SELECT 
        id,
        name,
        node_type,
        full_path as file_path,
        blast_radius,
        risk_level,
        fan_in
    FROM nodes
    WHERE repo_id = :repo_id
    AND blast_radius > 0
    ORDER BY blast_radius DESC
    LIMIT 20
    """
    try:
        result = await db.execute(text(query), {"repo_id": repo_id})
        rows = result.fetchall()
    except Exception as exc:
        logger.error("PostgreSQL top nodes query failed: %s", exc)
        raise HTTPException(status_code=500, detail="Query failed")

    return [
        NodeSearchResult(
            id=str(r.id),
            name=r.name,
            node_type=r.node_type,
            file_path=r.file_path,
            blast_radius=r.blast_radius or 0,
            risk_level=r.risk_level or "low",
            fan_in=r.fan_in or 0,
        )
        for r in rows
    ]


@router.get("/api/impact/history/{repo_id}", response_model=list[ImpactHistoryItem])
async def get_impact_history(
    repo_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Return the last 10 impact analyses run for this repo.
    Shown in the recommendations panel of the Impact page.
    """
    try:
        uid = UUID(repo_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail="Invalid repository id") from e

    repo = (await db.execute(
        select(Repo).where(Repo.id == uid, Repo.user_id == current_user.id)
    )).scalar_one_or_none()
    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found")

    from sqlalchemy import desc

    result = await db.execute(
        select(ImpactAnalysis)
        .where(ImpactAnalysis.repo_id == uid)
        .order_by(desc(ImpactAnalysis.created_at))
        .limit(10)
    )
    records = result.scalars().all()

    return [
        ImpactHistoryItem(
            id=str(r.id),
            node_id=r.node_id,
            node_name=r.node_name,
            node_type=r.node_type,
            risk_score=r.risk_score,
            risk_level=r.risk_level,
            blast_radius=r.blast_radius,
            created_at=r.created_at.isoformat() if r.created_at else "",
        )
        for r in records
    ]
