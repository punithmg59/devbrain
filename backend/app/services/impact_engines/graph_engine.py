"""Engine 2: Dependency Graph Engine — CTE traversal, edges, centrality (no LLM)."""

import asyncio
import logging
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.exc import DBAPIError, OperationalError
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

STATEMENT_TIMEOUT_SQL = text("SET LOCAL statement_timeout = '2s'")
TRAVERSAL_TIMEOUT_SECONDS = 2.0
TIMEOUT_WARNING = "Query timed out, showing partial results"

DOWNSTREAM_SQL = text("""
WITH RECURSIVE downstream AS (
    SELECT n.id, n.name, n.node_type,
           COALESCE(rf.file_path, '') as file_path,
           n.start_line, n.end_line, 0 as depth,
           'downstream' as direction, e2.edge_type,
           ARRAY[n.id::text] as visited
    FROM nodes n
    LEFT JOIN repo_files rf ON n.file_id = rf.id
    LEFT JOIN edges e2 ON e2.from_node_id = n.id
    WHERE n.id = :node_id AND n.repo_id = :repo_id
    UNION ALL
    SELECT n2.id, n2.name, n2.node_type,
           COALESCE(rf2.file_path, '') as file_path,
           n2.start_line, n2.end_line, ds.depth + 1,
           'downstream' as direction, e.edge_type,
           ds.visited || n2.id::text
    FROM downstream ds
    JOIN edges e ON e.from_node_id = ds.id
    JOIN nodes n2 ON n2.id = e.to_node_id
    LEFT JOIN repo_files rf2 ON n2.file_id = rf2.id
    WHERE ds.depth < :max_depth
      AND NOT n2.id::text = ANY(ds.visited)
      AND n2.repo_id = :repo_id
)
SELECT DISTINCT ON (id) id, name, node_type, file_path,
       start_line, end_line, depth, direction, edge_type
FROM downstream WHERE depth > 0 ORDER BY id, depth
""")

UPSTREAM_SQL = text("""
WITH RECURSIVE upstream AS (
    SELECT n.id, n.name, n.node_type,
           COALESCE(rf.file_path, '') as file_path,
           n.start_line, n.end_line, 0 as depth,
           'upstream' as direction, e2.edge_type,
           ARRAY[n.id::text] as visited
    FROM nodes n
    LEFT JOIN repo_files rf ON n.file_id = rf.id
    LEFT JOIN edges e2 ON e2.to_node_id = n.id
    WHERE n.id = :node_id AND n.repo_id = :repo_id
    UNION ALL
    SELECT n2.id, n2.name, n2.node_type,
           COALESCE(rf2.file_path, '') as file_path,
           n2.start_line, n2.end_line, us.depth + 1,
           'upstream' as direction, e.edge_type,
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
       start_line, end_line, depth, direction, edge_type
FROM upstream WHERE depth > 0 ORDER BY id, depth
""")


def _is_timeout(exc: Exception) -> bool:
    if isinstance(exc, asyncio.TimeoutError):
        return True
    msg = str(exc).lower()
    return "timeout" in msg or "canceled" in msg


class DependencyGraphEngine:
    def _row(self, row) -> dict:
        d = dict(row._mapping)
        if isinstance(d.get("id"), UUID):
            d["id"] = str(d["id"])
        if d.get("edge_type") is None:
            d["edge_type"] = ""
        return d

    async def traverse(self, ctx, db: AsyncSession) -> None:
        if not ctx.source_node:
            return

        direction = ctx.direction
        if ctx.scenario == "delete":
            direction = "upstream"
        elif ctx.scenario == "refactor":
            direction = "downstream" if ctx.direction == "both" else ctx.direction

        params = {
            "node_id": ctx.source_node["id"],
            "repo_id": ctx.repo_id,
            "max_depth": ctx.max_depth,
        }
        warning = None
        try:
            if direction == "downstream":
                nodes, warning = await self._run(DOWNSTREAM_SQL, params, db)
            elif direction == "upstream":
                nodes, warning = await self._run(UPSTREAM_SQL, params, db)
            else:
                down, w1 = await self._run(DOWNSTREAM_SQL, params, db)
                up, w2 = await self._run(UPSTREAM_SQL, params, db)
                warning = TIMEOUT_WARNING if (w1 or w2) else None
                nodes = self._merge(down, up)
        except (OperationalError, DBAPIError) as e:
            if _is_timeout(e):
                nodes, warning = [], TIMEOUT_WARNING
            else:
                raise
        except asyncio.TimeoutError:
            nodes, warning = [], TIMEOUT_WARNING

        ctx.impacted_nodes = nodes
        ctx.traversal_warning = warning

    async def _run(self, sql, params: dict, db: AsyncSession):
        async def _exec():
            await db.execute(STATEMENT_TIMEOUT_SQL)
            result = await db.execute(sql, params)
            return [self._row(r) for r in result]

        try:
            rows = await asyncio.wait_for(_exec(), timeout=TRAVERSAL_TIMEOUT_SECONDS)
            return rows, None
        except (asyncio.TimeoutError, OperationalError, DBAPIError) as e:
            if _is_timeout(e):
                return [], TIMEOUT_WARNING
            raise

    def _merge(self, down: list[dict], up: list[dict]) -> list[dict]:
        by_id: dict[str, dict] = {}
        for n in down + up:
            nid = n["id"]
            if nid not in by_id or n["depth"] < by_id[nid]["depth"]:
                by_id[nid] = n
        return list(by_id.values())

    async def enrich_metadata(self, ctx, db: AsyncSession) -> None:
        if not ctx.source_node:
            return
        ids = [ctx.source_node["id"]] + [n["id"] for n in ctx.impacted_nodes]
        if not ids:
            return
        sql = text("""
            SELECT id, http_method, route_path, summary, tags
            FROM nodes WHERE repo_id = :repo_id
            AND id = ANY(CAST(:ids AS uuid[]))
        """)
        result = await db.execute(sql, {"repo_id": ctx.repo_id, "ids": ids})
        meta = {str(r["id"]): dict(r) for r in result.mappings()}
        for n in [ctx.source_node, *ctx.impacted_nodes]:
            extra = meta.get(str(n["id"]), {})
            n["http_method"] = extra.get("http_method")
            n["route_path"] = extra.get("route_path")
            n["summary"] = extra.get("summary")
            n["tags"] = extra.get("tags") or []

    def attach_evidence(self, ctx) -> None:
        if not ctx.source_node:
            return
        src = ctx.source_node["name"]
        for n in ctx.impacted_nodes:
            n["inclusion_reason"] = (
                f"Verified edge: {n.get('direction')} from '{src}' "
                f"depth {n['depth']} via '{n.get('edge_type', 'calls')}'"
            )
            if n.get("node_type") == "api_route" and n.get("route_path"):
                n["inclusion_reason"] += (
                    f" — route {n.get('http_method', 'GET')} {n['route_path']}"
                )

    async def load_subgraph_edges(self, ctx, db: AsyncSession) -> None:
        ids = []
        if ctx.source_node:
            ids.append(ctx.source_node["id"])
        ids.extend(n["id"] for n in ctx.impacted_nodes[:120])
        if len(ids) < 2:
            ctx.graph_edges = []
            return
        sql = text("""
            SELECT from_node_id, to_node_id, edge_type
            FROM edges
            WHERE repo_id = :repo_id
              AND from_node_id = ANY(CAST(:ids AS uuid[]))
              AND to_node_id = ANY(CAST(:ids AS uuid[]))
        """)
        result = await db.execute(sql, {"repo_id": ctx.repo_id, "ids": ids})
        ctx.graph_edges = [
            {
                "from_id": str(r["from_node_id"]),
                "to_id": str(r["to_node_id"]),
                "edge_type": r["edge_type"] or "calls",
            }
            for r in result.mappings()
        ]

    def compute_centrality(self, ctx) -> None:
        """Degree centrality on verified subgraph only."""
        degree: dict[str, int] = {}
        for e in ctx.graph_edges:
            degree[e["from_id"]] = degree.get(e["from_id"], 0) + 1
            degree[e["to_id"]] = degree.get(e["to_id"], 0) + 1
        if not degree:
            ctx.centrality = {}
            return
        max_d = max(degree.values()) or 1
        ctx.centrality = {nid: round(d / max_d, 3) for nid, d in degree.items()}

    def build_blast_radius(self, ctx) -> None:
        nodes = ctx.impacted_nodes
        ctx.blast_radius = {
            "functions": sum(
                1 for n in nodes if n.get("node_type") in ("function", "method")
            ),
            "classes": sum(1 for n in nodes if n.get("node_type") == "class"),
            "api_routes": sum(1 for n in nodes if n.get("node_type") == "api_route"),
            "files": len({n.get("file_path") for n in nodes if n.get("file_path")}),
            "max_depth": max((n.get("depth", 0) for n in nodes), default=0),
            "total_nodes": len(nodes),
            "verified_edges": len(ctx.graph_edges),
            "scenario": ctx.scenario,
        }

    def extract_exact_dependencies(self, ctx) -> None:
        if not ctx.source_node:
            return
            
        exact = {
            "level_1_direct": [],
            "level_1_incoming": [],
            "level_2_indirect": [],
            "level_3_workflow": [],
            "database_dependencies": [],
            "api_dependencies": [],
            "file_dependencies": []
        }
        
        files = set()
        
        for n in ctx.impacted_nodes:
            item = {
                "id": n["id"],
                "name": n["name"],
                "node_type": n.get("node_type", "unknown"),
                "file_path": n.get("file_path", ""),
                "confidence": 1.0  # Default confidence
            }
            
            if item["file_path"]:
                files.add(item["file_path"])
                
            depth = n.get("depth", 1)
            direction = n.get("direction", "downstream")
            
            if depth == 1:
                if direction == "downstream":
                    exact["level_1_direct"].append(item)
                else:
                    exact["level_1_incoming"].append(item)
            elif depth == 2:
                exact["level_2_indirect"].append(item)
            elif depth >= 3:
                exact["level_3_workflow"].append(item)
                
            # Type-based dependencies
            ntype = item["node_type"].lower()
            if ntype in ["database", "table", "db", "model"]:
                exact["database_dependencies"].append(item)
            elif ntype in ["api_route", "endpoint", "route"]:
                exact["api_dependencies"].append(item)
                
        exact["file_dependencies"] = list(files)
        ctx.exact_dependencies = exact
