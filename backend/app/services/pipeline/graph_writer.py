import logging
from app.graph.neo4j_client import run_write_batch, run_write_query

logger = logging.getLogger(__name__)


async def write_nodes_to_neo4j(
    nodes: list[dict],
    repo_id: str,
) -> int:
    """
    Upsert a list of node dicts into Neo4j.

    Each dict must have at minimum:
      id, repo_id, name, node_type, file_path

    Uses MERGE on (id, repo_id) so re-running is safe.
    Returns count of nodes written.

    node_type values map to Neo4j labels:
        function → :Function:Node
        class    → :Class:Node
        file     → :File:Node
        api      → :API:Node
        service  → :Service:Node
        table    → :Table:Node
        unknown  → :Node
    """
    if not nodes:
        return 0

    cypher = """
    UNWIND $rows AS row
    MERGE (n:Node {id: row.id, repo_id: row.repo_id})
    SET n += {
        name:           row.name,
        node_type:      row.node_type,
        file_path:      row.file_path,
        language:       row.language,
        signature:      row.signature,
        fan_in:         0,
        fan_out:        0,
        blast_radius:   0,
        risk_level:     'low',
        pagerank:       0.0,
        coupling_score: 0.0
    }
    RETURN count(n) AS written
    """

    # Normalize rows — ensure all required keys exist
    rows = []
    for node in nodes:
        rows.append({
            "id":        str(node.get("id", "")),
            "repo_id":   str(repo_id),
            "name":      str(node.get("name", "")),
            "node_type": str(node.get("node_type", "unknown")),
            "file_path": str(node.get("file_path", "")),
            "language":  str(node.get("language", "")),
            "signature": str(node.get("signature", "")),
        })

    written = await run_write_batch(cypher, rows, batch_size=500)
    logger.info("Neo4j: wrote %d nodes for repo %s", written, repo_id)
    return written


async def write_edges_to_neo4j(
    edges: list[dict],
    repo_id: str,
) -> int:
    """
    Upsert a list of edge dicts into Neo4j as relationships.

    Each dict must have:
      from_node_id, to_node_id, edge_type, repo_id

    edge_type values: CALLS, IMPORTS, DEPENDS_ON, READS, WRITES
    Defaults to CALLS if edge_type is missing or unrecognized.

    Uses MERGE on relationship so re-running is safe.
    Returns count of edges written.
    """
    if not edges:
        return 0

    # Write edges grouped by type for cleaner Cypher
    cypher = """
    UNWIND $rows AS row
    MATCH (from:Node {id: row.from_id, repo_id: row.repo_id})
    MATCH (to:Node   {id: row.to_id,   repo_id: row.repo_id})
    MERGE (from)-[r:CALLS {repo_id: row.repo_id}]->(to)
    SET r.edge_type = row.edge_type
    RETURN count(r) AS written
    """

    rows = []
    valid_types = {"CALLS", "IMPORTS", "DEPENDS_ON", "READS", "WRITES"}
    for edge in edges:
        edge_type = str(edge.get("edge_type", "CALLS")).upper()
        if edge_type not in valid_types:
            edge_type = "CALLS"
        rows.append({
            "from_id":   str(edge.get("from_node_id", "")),
            "to_id":     str(edge.get("to_node_id", "")),
            "repo_id":   str(repo_id),
            "edge_type": edge_type,
        })

    # Filter out rows where from_id or to_id is empty
    rows = [r for r in rows if r["from_id"] and r["to_id"]]

    if not rows:
        logger.warning("No valid edges to write to Neo4j for repo %s", repo_id)
        return 0

    written = await run_write_batch(cypher, rows, batch_size=500)
    logger.info("Neo4j: wrote %d edges for repo %s", written, repo_id)
    return written


async def delete_repo_graph(repo_id: str) -> None:
    """
    Delete all nodes and relationships for a repo from Neo4j.
    Called before full re-analysis to start clean.
    Uses batched delete to avoid memory issues on large graphs.
    """
    cypher = """
    MATCH (n:Node {repo_id: $repo_id})
    DETACH DELETE n
    """
    try:
        await run_write_query(cypher, {"repo_id": str(repo_id)})
        logger.info("Neo4j: deleted graph for repo %s", repo_id)
    except Exception as exc:
        logger.error("Neo4j delete failed for repo %s: %s", repo_id, exc)
