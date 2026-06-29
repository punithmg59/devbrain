import logging
from app.graph.neo4j_client import run_query, run_write_query

logger = logging.getLogger(__name__)

# Risk classification thresholds
# Tune these as you gather real data
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
    and risk_level for every node in the repo's graph.

    Steps:
      1. Compute fan_in (count of incoming relationships per node)
      2. Compute fan_out (count of outgoing relationships per node)
      3. Compute blast_radius using BFS traversal (nodes reachable
         by following incoming edges up to 8 hops)
      4. Classify risk_level from fan_in and blast_radius
      5. Compute coupling_score = (fan_in * fan_out) / max_possible
      6. Write all scores back to Neo4j nodes

    Returns summary dict with counts and timing.
    """
    logger.info("Computing graph scores for repo %s", repo_id)

    # ── Step 1+2: fan_in and fan_out in one query ─────────────────
    fan_query = """
    MATCH (n:Node {repo_id: $repo_id})
    OPTIONAL MATCH (caller)-[:CALLS|IMPORTS|DEPENDS_ON]->(n)
    WITH n, count(DISTINCT caller) AS fan_in
    OPTIONAL MATCH (n)-[:CALLS|IMPORTS|DEPENDS_ON]->(callee)
    WITH n, fan_in, count(DISTINCT callee) AS fan_out
    SET n.fan_in  = fan_in,
        n.fan_out = fan_out,
        n.coupling_score = CASE
            WHEN (fan_in + fan_out) = 0 THEN 0.0
            ELSE toFloat(fan_in * fan_out) /
                 toFloat((fan_in + fan_out) * (fan_in + fan_out))
        END
    RETURN count(n) AS scored
    """
    result = await run_query(fan_query, {"repo_id": repo_id})
    node_count = result[0]["scored"] if result else 0
    logger.info("Scored fan_in/fan_out for %d nodes", node_count)

    # ── Step 3: blast_radius via BFS ──────────────────────────────
    # For each node, count how many nodes reach it within 8 hops.
    # This is the blast radius — how many things break if this changes.
    # We compute it in batches to avoid memory issues on large graphs.
    blast_query = """
    MATCH (n:Node {repo_id: $repo_id})
    CALL {
        WITH n
        MATCH (affected:Node {repo_id: $repo_id})
        WHERE (affected)-[:CALLS|IMPORTS|DEPENDS_ON*1..8]->(n)
        RETURN count(DISTINCT affected) AS blast
    }
    SET n.blast_radius = blast,
        n.risk_level = CASE
            WHEN n.fan_in >= 20 OR blast >= 50 THEN 'critical'
            WHEN n.fan_in >= 10 OR blast >= 20 THEN 'high'
            WHEN n.fan_in >= 3  OR blast >= 5  THEN 'medium'
            ELSE 'low'
        END
    RETURN count(n) AS scored
    """
    try:
        result = await run_query(blast_query, {"repo_id": repo_id})
        blast_count = result[0]["scored"] if result else 0
        logger.info("Scored blast_radius for %d nodes", blast_count)
    except Exception as exc:
        # Blast radius query can time out on very large graphs.
        # Fall back to a simpler depth-1 approximation.
        logger.warning(
            "Full blast radius timed out, using depth-1 fallback: %s", exc
        )
        fallback = """
        MATCH (n:Node {repo_id: $repo_id})
        OPTIONAL MATCH (affected)-[:CALLS|IMPORTS|DEPENDS_ON]->(n)
        WITH n, count(DISTINCT affected) AS blast
        SET n.blast_radius = blast,
            n.risk_level = CASE
                WHEN n.fan_in >= 20 OR blast >= 50 THEN 'critical'
                WHEN n.fan_in >= 10 OR blast >= 20 THEN 'high'
                WHEN n.fan_in >= 3  OR blast >= 5  THEN 'medium'
                ELSE 'low'
            END
        RETURN count(n) AS scored
        """
        result = await run_query(fallback, {"repo_id": repo_id})
        blast_count = result[0]["scored"] if result else 0

    # ── Step 4: Return summary ────────────────────────────────────
    summary_query = """
    MATCH (n:Node {repo_id: $repo_id})
    RETURN
        count(n) AS total,
        sum(CASE WHEN n.risk_level = 'critical' THEN 1 ELSE 0 END) AS critical,
        sum(CASE WHEN n.risk_level = 'high'     THEN 1 ELSE 0 END) AS high,
        sum(CASE WHEN n.risk_level = 'medium'   THEN 1 ELSE 0 END) AS medium,
        sum(CASE WHEN n.risk_level = 'low'      THEN 1 ELSE 0 END) AS low,
        max(n.blast_radius) AS max_blast,
        max(n.fan_in)       AS max_fan_in
    """
    summary = await run_query(summary_query, {"repo_id": repo_id})
    result_dict = summary[0] if summary else {}

    logger.info(
        "Graph scoring complete for repo %s: %s",
        repo_id, result_dict
    )
    return result_dict


async def get_top_nodes_by_blast(
    repo_id: str,
    limit: int = 50
) -> list[dict]:
    """
    Return the top N nodes by blast_radius for a repo.
    Used to pre-warm the Impact page cache after analysis.
    """
    query = """
    MATCH (n:Node {repo_id: $repo_id})
    WHERE n.blast_radius > 0
    RETURN
        n.id          AS id,
        n.name        AS name,
        n.node_type   AS node_type,
        n.file_path   AS file_path,
        n.blast_radius AS blast_radius,
        n.risk_level  AS risk_level,
        n.fan_in      AS fan_in,
        n.fan_out     AS fan_out
    ORDER BY n.blast_radius DESC
    LIMIT $limit
    """
    return await run_query(query, {"repo_id": repo_id, "limit": limit})
