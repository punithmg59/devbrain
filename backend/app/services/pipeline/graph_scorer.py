import logging
import uuid
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

    # FIX: asyncpg binary protocol sends Python str as PostgreSQL TEXT (OID 25).
    # nodes.repo_id / edges.repo_id are UUID columns (OID 2950). Passing str
    # causes a silent type mismatch — UPDATE/SELECT WHERE clauses match 0 rows.
    # Converting to uuid.UUID ensures asyncpg sends OID 2950, matching the column.
    repo_uuid = uuid.UUID(repo_id) if not isinstance(repo_id, uuid.UUID) else repo_id
    logger.info(
        "GraphScorer repo_id=%s type=%s",
        repo_uuid,
        type(repo_uuid),
    )

    async with async_session_factory() as db:
        param_obj = {"repo_id": str(repo_uuid)}

        # 1. Initial nodes check
        q_init_nodes = "SELECT COUNT(*) FROM nodes WHERE repo_id = CAST(:repo_id AS uuid)"
        res_init_nodes = (await db.execute(text(q_init_nodes), param_obj)).scalar() or 0
        logger.info(
            "[INSTRUMENTATION] Initial Nodes Check:\n"
            "  SQL: %s\n"
            "  Bound Params: %s (Type: %s)\n"
            "  Affected Rows: N/A\n"
            "  Returned Count: %d",
            q_init_nodes, param_obj, type(param_obj["repo_id"]), res_init_nodes
        )

        # 2. Initial edges check
        q_init_edges = "SELECT COUNT(*) FROM edges WHERE repo_id = CAST(:repo_id AS uuid)"
        res_init_edges = (await db.execute(text(q_init_edges), param_obj)).scalar() or 0
        logger.info(
            "[INSTRUMENTATION] Initial Edges Check:\n"
            "  SQL: %s\n"
            "  Bound Params: %s (Type: %s)\n"
            "  Affected Rows: N/A\n"
            "  Returned Count: %d",
            q_init_edges, param_obj, type(param_obj["repo_id"]), res_init_edges
        )

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
            WHERE repo_id = CAST(:repo_id AS uuid)
            GROUP BY from_node_id
        ) outgoing
        FULL OUTER JOIN (
            SELECT 
                to_node_id,
                COUNT(*) as count
            FROM edges
            WHERE repo_id = CAST(:repo_id AS uuid)
            GROUP BY to_node_id
        ) incoming ON outgoing.from_node_id = incoming.to_node_id
        WHERE n.id = COALESCE(outgoing.from_node_id, incoming.to_node_id)
        AND n.repo_id = CAST(:repo_id AS uuid)
        """
        fan_res = await db.execute(text(fan_query), param_obj)
        logger.info(
            "[INSTRUMENTATION] fan_in/fan_out UPDATE:\n"
            "  SQL: %s\n"
            "  Bound Params: %s (Type: %s)\n"
            "  Affected Rows (rowcount): %s\n"
            "  Returned Rows: N/A",
            fan_query.strip(), param_obj, type(param_obj["repo_id"]), fan_res.rowcount
        )
        
        # Post fan_in update check
        q_fan_check = "SELECT COUNT(*) FROM nodes WHERE fan_in IS NOT NULL AND repo_id = CAST(:repo_id AS uuid)"
        res_fan_check = (await db.execute(text(q_fan_check), param_obj)).scalar() or 0
        logger.info(
            "[INSTRUMENTATION] Post-fan UPDATE Node Count:\n"
            "  SQL: %s\n"
            "  Bound Params: %s (Type: %s)\n"
            "  Affected Rows: N/A\n"
            "  Returned Count: %d",
            q_fan_check, param_obj, type(param_obj["repo_id"]), res_fan_check
        )

        # Step 3: blast_radius via recursive CTE
        blast_query = """
        WITH RECURSIVE blast_radius AS (
            -- Base case: nodes that directly call the target
            SELECT 
                e.to_node_id as target_id,
                e.from_node_id as affected_id,
                1 as depth
            FROM edges e
            WHERE e.repo_id = CAST(:repo_id AS uuid)
            
            UNION ALL
            
            -- Recursive case: nodes that call nodes that call the target
            SELECT 
                br.target_id,
                e.from_node_id as affected_id,
                br.depth + 1 as depth
            FROM blast_radius br
            JOIN edges e ON e.to_node_id = br.affected_id
            WHERE e.repo_id = CAST(:repo_id AS uuid)
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
        AND n.repo_id = CAST(:repo_id AS uuid)
        """
        try:
            blast_res = await db.execute(text(blast_query), param_obj)
            logger.info(
                "[INSTRUMENTATION] blast_radius UPDATE:\n"
                "  SQL: %s\n"
                "  Bound Params: %s (Type: %s)\n"
                "  Affected Rows (rowcount): %s\n"
                "  Returned Rows: N/A",
                blast_query.strip(), param_obj, type(param_obj["repo_id"]), blast_res.rowcount
            )
        except Exception as exc:
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
                WHERE repo_id = CAST(:repo_id AS uuid)
                GROUP BY to_node_id
            ) incoming
            WHERE n.id = incoming.to_node_id
            AND n.repo_id = CAST(:repo_id AS uuid)
            """
            fallback_res = await db.execute(text(fallback), param_obj)
            logger.info(
                "[INSTRUMENTATION] blast_radius Fallback UPDATE:\n"
                "  SQL: %s\n"
                "  Bound Params: %s (Type: %s)\n"
                "  Affected Rows (rowcount): %s\n"
                "  Returned Rows: N/A",
                fallback.strip(), param_obj, type(param_obj["repo_id"]), fallback_res.rowcount
            )

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
        WHERE repo_id = CAST(:repo_id AS uuid)
        """
        result = await db.execute(text(summary_query), param_obj)
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

        logger.info(
            "[INSTRUMENTATION] Summary Query:\n"
            "  SQL: %s\n"
            "  Bound Params: %s (Type: %s)\n"
            "  Affected Rows: N/A\n"
            "  Returned Result: %s",
            summary_query.strip(), param_obj, type(param_obj["repo_id"]), result_dict
        )

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
    # FIX: same UUID/TEXT type mismatch fix applied here as in compute_scores().
    repo_uuid = uuid.UUID(repo_id) if not isinstance(repo_id, uuid.UUID) else repo_id

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
        WHERE repo_id = :repo_id::uuid
        AND blast_radius > 0
        ORDER BY blast_radius DESC
        LIMIT :limit
        """
        result = await db.execute(text(query), {"repo_id": str(repo_uuid), "limit": limit})
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

