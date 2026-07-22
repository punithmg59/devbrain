import logging
from sqlalchemy import select, func, text, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import async_session_factory
from app.models.node import Node
from app.models.edge import Edge

logger = logging.getLogger(__name__)

# Risk classification thresholds
RISK_THRESHOLDS = {
    "critical": {"blast_radius": 50, "fan_in": 20},
    "high":     {"blast_radius": 20, "fan_in": 10},
    "medium":   {"blast_radius": 5,  "fan_in": 3},
}


def _classify_risk(fan_in: int, blast_radius: int) -> str:
    """Classify risk level based on fan_in and blast_radius."""
    if (fan_in >= RISK_THRESHOLDS["critical"]["fan_in"] or
            blast_radius >= RISK_THRESHOLDS["critical"]["blast_radius"]):
        return "critical"
    if (fan_in >= RISK_THRESHOLDS["high"]["fan_in"] or
            blast_radius >= RISK_THRESHOLDS["high"]["blast_radius"]):
        return "high"
    if (fan_in >= RISK_THRESHOLDS["medium"]["fan_in"] or
            blast_radius >= RISK_THRESHOLDS["medium"]["blast_radius"]):
        return "medium"
    return "low"


async def compute_scores(repo_id: str) -> dict:
    """
    Compute and persist fan_in, fan_out, blast_radius, coupling_score,
    and risk_level for every node in the repo's graph using PostgreSQL.

    Steps:
      1. Compute fan_in (count of incoming edges per node)
      2. Compute fan_out (count of outgoing edges per node)
      3. Compute blast_radius using recursive CTE traversal
      4. Classify risk_level from fan_in and blast_radius
      5. Compute coupling_score = (fan_in * fan_out) / max_possible
      6. Write all scores back to PostgreSQL nodes

    Returns summary dict with counts and timing.
    """
    logger.info("Computing graph scores for repo %s", repo_id)

    async with async_session_factory() as db:
        # Step 1+2: fan_in and fan_out using SQL
        fan_query = """
        UPDATE nodes n
        SET 
            fan_in = COALESCE(incoming.count, 0),
            fan_out = COALESCE(outgoing.count, 0),
            coupling_score = CASE
                WHEN (COALESCE(incoming.count, 0) + COALESCE(outgoing.count, 0)) = 0 THEN 0.0
                ELSE CAST(COALESCE(incoming.count, 0) * COALESCE(outgoing.count, 0) AS FLOAT) / 
                     CAST(POWER(COALESCE(incoming.count, 0) + COALESCE(outgoing.count, 0), 2) AS FLOAT)
            END
        FROM (
            SELECT 
                from_node_id,
                COUNT(*) as count
            FROM edges
            WHERE repo_id = :repo_id
            GROUP BY from_node_id
        ) outgoing
        FULL OUTER JOIN (
            SELECT 
                to_node_id,
                COUNT(*) as count
            FROM edges
            WHERE repo_id = :repo_id
            GROUP BY to_node_id
        ) incoming ON outgoing.from_node_id = incoming.to_node_id
        WHERE n.id = COALESCE(outgoing.from_node_id, incoming.to_node_id)
        AND n.repo_id = :repo_id
        """
        await db.execute(text(fan_query), {"repo_id": repo_id})
        
        # Get node count
        node_count_result = await db.execute(
            select(func.count()).select_from(Node).where(Node.repo_id == repo_id)
        )
        node_count = node_count_result.scalar() or 0
        logger.info("Scored fan_in/fan_out for %d nodes", node_count)

        # Step 3: blast_radius via recursive CTE
        # For each node, count how many nodes reach it within 8 hops
        blast_query = """
        WITH RECURSIVE blast_radius AS (
            -- Base case: nodes that directly call the target
            SELECT 
                e.to_node_id as target_id,
                e.from_node_id as affected_id,
                1 as depth
            FROM edges e
            WHERE e.repo_id = :repo_id
            
            UNION ALL
            
            -- Recursive case: nodes that call nodes that call the target
            SELECT 
                br.target_id,
                e.from_node_id as affected_id,
                br.depth + 1 as depth
            FROM blast_radius br
            JOIN edges e ON e.to_node_id = br.affected_id
            WHERE e.repo_id = :repo_id
            AND br.depth < 8
            AND e.from_node_id != br.target_id
        )
        UPDATE nodes n
        SET 
            blast_radius = COALESCE(br.count, 0),
            risk_level = CASE
                WHEN n.fan_in >= 20 OR COALESCE(br.count, 0) >= 50 THEN 'critical'
                WHEN n.fan_in >= 10 OR COALESCE(br.count, 0) >= 20 THEN 'high'
                WHEN n.fan_in >= 3  OR COALESCE(br.count, 0) >= 5  THEN 'medium'
                ELSE 'low'
            END
        FROM (
            SELECT target_id, COUNT(DISTINCT affected_id) as count
            FROM blast_radius
            GROUP BY target_id
        ) br
        WHERE n.id = br.target_id
        AND n.repo_id = :repo_id
        """
        try:
            await db.execute(text(blast_query), {"repo_id": repo_id})
            logger.info("Scored blast_radius for nodes")
        except Exception as exc:
            # Blast radius query can time out on very large graphs
            # Fall back to a simpler depth-1 approximation
            logger.warning("Full blast radius timed out, using depth-1 fallback: %s", exc)
            fallback = """
            UPDATE nodes n
            SET 
                blast_radius = COALESCE(incoming.count, 0),
                risk_level = CASE
                    WHEN n.fan_in >= 20 OR COALESCE(incoming.count, 0) >= 50 THEN 'critical'
                    WHEN n.fan_in >= 10 OR COALESCE(incoming.count, 0) >= 20 THEN 'high'
                    WHEN n.fan_in >= 3  OR COALESCE(incoming.count, 0) >= 5  THEN 'medium'
                    ELSE 'low'
                END
            FROM (
                SELECT 
                    to_node_id,
                    COUNT(*) as count
                FROM edges
                WHERE repo_id = :repo_id
                GROUP BY to_node_id
            ) incoming
            WHERE n.id = incoming.to_node_id
            AND n.repo_id = :repo_id
            """
            await db.execute(text(fallback), {"repo_id": repo_id})

        await db.commit()

        # Step 4: Return summary
        summary_query = """
        SELECT
            COUNT(*) as total,
            SUM(CASE WHEN risk_level = 'critical' THEN 1 ELSE 0 END) as critical,
            SUM(CASE WHEN risk_level = 'high' THEN 1 ELSE 0 END) as high,
            SUM(CASE WHEN risk_level = 'medium' THEN 1 ELSE 0 END) as medium,
            SUM(CASE WHEN risk_level = 'low' THEN 1 ELSE 0 END) as low,
            MAX(blast_radius) as max_blast,
            MAX(fan_in) as max_fan_in
        FROM nodes
        WHERE repo_id = :repo_id
        """
        result = await db.execute(text(summary_query), {"repo_id": repo_id})
        summary = result.first()
        result_dict = {
            "total": summary.total if summary else 0,
            "critical": summary.critical if summary else 0,
            "high": summary.high if summary else 0,
            "medium": summary.medium if summary else 0,
            "low": summary.low if summary else 0,
            "max_blast": summary.max_blast if summary else 0,
            "max_fan_in": summary.max_fan_in if summary else 0,
        }

        logger.info("Graph scoring complete for repo %s: %s", repo_id, result_dict)
        return result_dict


async def get_top_nodes_by_blast(
    repo_id: str,
    limit: int = 50
) -> list[dict]:
    """
    Return the top N nodes by blast_radius for a repo using PostgreSQL.
    Used to pre-warm the Impact page cache after analysis.
    """
    async with async_session_factory() as db:
        query = """
        SELECT 
            id,
            name,
            node_type,
            full_path as file_path,
            blast_radius,
            risk_level,
            fan_in,
            fan_out
        FROM nodes
        WHERE repo_id = :repo_id
        AND blast_radius > 0
        ORDER BY blast_radius DESC
        LIMIT :limit
        """
        result = await db.execute(text(query), {"repo_id": repo_id, "limit": limit})
        rows = result.fetchall()
        
        return [
            {
                "id": str(row.id),
                "name": row.name,
                "node_type": row.node_type,
                "file_path": row.file_path,
                "blast_radius": row.blast_radius,
                "risk_level": row.risk_level,
                "fan_in": row.fan_in,
                "fan_out": row.fan_out,
            }
            for row in rows
        ]

