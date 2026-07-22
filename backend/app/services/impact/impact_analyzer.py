import logging
import time
from datetime import datetime, timezone
from sqlalchemy import select, func, text
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import async_session_factory
from app.models.node import Node
from app.models.edge import Edge
from app.schemas.impact import (
    SimpleImpactResult,
    AffectedNode,
    RiskScore,
    EffortEstimate,
    SimpleGraphEdge,
)

logger = logging.getLogger(__name__)

# ── In-memory cache ───────────────────────────────────────────────
# Simple dict cache — good enough for MVP.
# Key: "{node_id}:{repo_id}"  Value: (ImpactResult, timestamp)
# Entries expire after CACHE_TTL_SECONDS.

_cache: dict[str, tuple] = {}
CACHE_TTL_SECONDS = 3600  # 1 hour


def _cache_get(node_id: str, repo_id: str) -> SimpleImpactResult | None:
    key = f"{node_id}:{repo_id}"
    entry = _cache.get(key)
    if entry and (time.monotonic() - entry[1]) < CACHE_TTL_SECONDS:
        return entry[0]
    return None


def _cache_set(node_id: str, repo_id: str, result: SimpleImpactResult) -> None:
    key = f"{node_id}:{repo_id}"
    _cache[key] = (result, time.monotonic())


def _cache_invalidate_repo(repo_id: str) -> None:
    """Call this when a new analysis completes for a repo."""
    keys_to_delete = [k for k in _cache if k.endswith(f":{repo_id}")]
    for k in keys_to_delete:
        del _cache[k]


# ── Risk scoring ──────────────────────────────────────────────────

def _calculate_risk_score(
    blast_radius: int,
    fan_in: int,
    affected_api_count: int,
    max_depth: int,
) -> RiskScore:
    """
    Calculate a 0-10 risk score based on blast radius and connectivity.

    Formula:
        base   = min(blast_radius / 10, 5.0)      ← up to 5 points
        conn   = min(fan_in / 10, 2.0)            ← up to 2 points
        api    = min(affected_api_count * 0.5, 2.0) ← up to 2 points
        depth  = min(max_depth * 0.1, 1.0)        ← up to 1 point
        total  = base + conn + api + depth         ← 0 to 10

    Returns RiskScore with value, level, and plain English explanation.
    """
    base = min(blast_radius / 10, 5.0)
    conn = min(fan_in / 10, 2.0)
    api = min(affected_api_count * 0.5, 2.0)
    depth = min(max_depth * 0.1, 1.0)
    value = round(base + conn + api + depth, 1)

    if value >= 7.5:
        level = "critical"
        explanation = (
            f"Changing this component affects {blast_radius} other components "
            f"including {affected_api_count} APIs. "
            "Requires careful planning and full test coverage before merging."
        )
    elif value >= 5.0:
        level = "high"
        explanation = (
            f"This change ripples through {blast_radius} components. "
            "Coordinate with dependent team members before changing."
        )
    elif value >= 2.5:
        level = "medium"
        explanation = (
            f"Moderate impact — {blast_radius} components affected. "
            "Review callers before making changes."
        )
    else:
        level = "low"
        explanation = (
            f"Low impact change. {blast_radius} components affected. "
            "Standard review process applies."
        )

    return RiskScore(value=value, level=level, explanation=explanation)


def _estimate_effort(blast_radius: int, risk_level: str) -> EffortEstimate:
    """Estimate engineering effort to safely change this component."""
    multiplier = {"low": 1.0, "medium": 1.5, "high": 2.5, "critical": 4.0}
    base_hours = max(blast_radius * 0.5, 0.5)
    hours = round(base_hours * multiplier.get(risk_level, 1.0), 1)

    if hours < 2:
        label = f"~{int(hours * 60)} minutes"
    elif hours < 8:
        label = f"~{int(hours)} hours"
    elif hours < 40:
        days = round(hours / 8, 1)
        label = f"~{days} days"
    else:
        weeks = round(hours / 40, 1)
        label = f"~{weeks} weeks"

    return EffortEstimate(
        hours=hours,
        label=label,
        confidence=0.65,
    )


# ── Main analyzer ─────────────────────────────────────────────────

async def analyze_impact(node_id: str, repo_id: str) -> SimpleImpactResult:
    """
    Run full impact analysis for a node using PostgreSQL.

    Steps:
        1. Check cache — return immediately if cached
        2. Fetch target node details from PostgreSQL
        3. Run blast radius traversal (recursive CTE via incoming edges, 8 hops)
        4. Classify affected nodes by type
        5. Build graph edges for visualization
        6. Calculate risk score and effort estimate
        7. Store in cache
        8. Return ImpactResult

    Recommendations are NOT generated here — they are generated
    separately by the router to allow streaming.
    """
    # Step 1: cache check
    cached = _cache_get(node_id, repo_id)
    if cached:
        logger.info("Impact cache hit for node %s", node_id)
        return cached

    async with async_session_factory() as db:
        # Step 2: fetch target node
        target_query = """
        SELECT 
            id,
            name,
            node_type,
            full_path as file_path,
            fan_in,
            fan_out,
            blast_radius,
            risk_level
        FROM nodes
        WHERE id = :node_id
        AND repo_id = :repo_id
        """
        target_result = await db.execute(text(target_query), {"node_id": node_id, "repo_id": repo_id})
        target_row = target_result.first()
        if not target_row:
            raise ValueError(f"Node {node_id} not found in repo {repo_id}")

        target = {
            "id": str(target_row.id),
            "name": target_row.name,
            "node_type": target_row.node_type,
            "file_path": target_row.file_path,
            "fan_in": target_row.fan_in or 0,
            "fan_out": target_row.fan_out or 0,
            "blast_radius": target_row.blast_radius or 0,
            "risk_level": target_row.risk_level or "low",
        }

        # Step 3: blast radius traversal using recursive CTE
        # Follow incoming edges — who calls/depends on this node?
        # Return each affected node with its traversal depth.
        traversal_query = """
        WITH RECURSIVE affected_nodes AS (
            -- Base case: nodes that directly call the target
            SELECT 
                e.from_node_id as id,
                n.name,
                n.node_type,
                n.full_path as file_path,
                n.risk_level,
                n.fan_in,
                n.fan_out,
                1 as depth
            FROM edges e
            JOIN nodes n ON n.id = e.from_node_id
            WHERE e.to_node_id = :node_id
            AND e.repo_id = :repo_id
            AND n.repo_id = :repo_id
            AND e.from_node_id != :node_id
            
            UNION ALL
            
            -- Recursive case: nodes that call nodes that call the target
            SELECT 
                e.from_node_id as id,
                n.name,
                n.node_type,
                n.full_path as file_path,
                n.risk_level,
                n.fan_in,
                n.fan_out,
                an.depth + 1 as depth
            FROM affected_nodes an
            JOIN edges e ON e.to_node_id = an.id
            JOIN nodes n ON n.id = e.from_node_id
            WHERE e.repo_id = :repo_id
            AND n.repo_id = :repo_id
            AND e.from_node_id != :node_id
            AND an.depth < 8
        )
        SELECT DISTINCT ON (id)
            id,
            name,
            node_type,
            file_path,
            risk_level,
            fan_in,
            fan_out,
            MIN(depth) as depth
        FROM affected_nodes
        ORDER BY id, depth ASC
        LIMIT 200
        """
        affected_result = await db.execute(text(traversal_query), {"node_id": node_id, "repo_id": repo_id})
        affected_rows = affected_result.fetchall()

        # Step 4: classify by type
        affected_nodes = []
        affected_apis = []
        affected_services = []
        affected_tables = []

        for row in affected_rows:
            node = AffectedNode(
                id=str(row.id),
                name=row.name,
                node_type=row.node_type,
                file_path=row.file_path,
                risk_level=row.risk_level or "low",
                depth=row.depth,
                fan_in=row.fan_in or 0,
                fan_out=row.fan_out or 0,
            )
            affected_nodes.append(node)
            t = node.node_type.lower()
            if t in ("api", "endpoint", "route"):
                affected_apis.append(node)
            elif t in ("service",):
                affected_services.append(node)
            elif t in ("table", "model", "entity"):
                affected_tables.append(node)

        # Step 5: build graph edges for visualization
        edges_query = """
        SELECT 
            e.from_node_id as source,
            e.to_node_id as target,
            e.edge_type
        FROM edges e
        WHERE e.repo_id = :repo_id
        AND e.from_node_id IN (
            SELECT from_node_id FROM edges WHERE to_node_id = :node_id AND repo_id = :repo_id
            UNION
            SELECT to_node_id FROM edges WHERE from_node_id = :node_id AND repo_id = :repo_id
        )
        AND e.to_node_id IN (
            SELECT from_node_id FROM edges WHERE to_node_id = :node_id AND repo_id = :repo_id
            UNION
            SELECT to_node_id FROM edges WHERE from_node_id = :node_id AND repo_id = :repo_id
        )
        LIMIT 500
        """
        try:
            edge_result = await db.execute(text(edges_query), {"node_id": node_id, "repo_id": repo_id})
            edge_rows = edge_result.fetchall()
        except Exception:
            edge_rows = []

        graph_edges = [
            SimpleGraphEdge(
                source=str(r.source),
                target=str(r.target),
                edge_type=r.edge_type,
                is_critical=(r.edge_type == "CALLS"),
            )
            for r in edge_rows
            if r.source and r.target
        ]

        # Step 6: scores
        max_depth = max((n.depth for n in affected_nodes), default=0)
        risk_score = _calculate_risk_score(
            blast_radius=len(affected_nodes),
            fan_in=target.get("fan_in") or 0,
            affected_api_count=len(affected_apis),
            max_depth=max_depth,
        )
        effort = _estimate_effort(len(affected_nodes), risk_score.level)

        # Step 7: build result
        result = SimpleImpactResult(
            node_id=node_id,
            node_name=target.get("name", ""),
            node_type=target.get("node_type", "unknown"),
            file_path=target.get("file_path", ""),
            risk_score=risk_score,
            blast_radius=len(affected_nodes),
            effort_estimate=effort,
            affected_nodes=affected_nodes,
            affected_apis=affected_apis,
            affected_services=affected_services,
            affected_tables=affected_tables,
            graph_edges=graph_edges,
            recommendations=[],  # filled by router
            repo_id=repo_id,
            analyzed_at=datetime.now(timezone.utc).isoformat(),
        )

        # Step 8: cache
        _cache_set(node_id, repo_id, result)
        return result
