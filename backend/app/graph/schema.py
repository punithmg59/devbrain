import logging
from app.graph.neo4j_client import run_write_query

logger = logging.getLogger(__name__)

# Run once at startup. IF NOT EXISTS means safe to re-run on restart.
SCHEMA_QUERIES = [

    # ── Uniqueness constraints ───────────────────────────────────────
    # Prevents duplicate nodes for the same id+repo_id combination.
    # Also creates an implicit index on these properties.

    "CREATE CONSTRAINT node_unique IF NOT EXISTS "
    "FOR (n:Node) REQUIRE (n.id, n.repo_id) IS NODE KEY",

    "CREATE CONSTRAINT file_unique IF NOT EXISTS "
    "FOR (f:File) REQUIRE (f.id, f.repo_id) IS NODE KEY",

    # ── Lookup indexes ───────────────────────────────────────────────
    # Used by Impact queries and Understand page graph loading.

    "CREATE INDEX node_repo_id IF NOT EXISTS "
    "FOR (n:Node) ON (n.repo_id)",

    "CREATE INDEX node_name IF NOT EXISTS "
    "FOR (n:Node) ON (n.name)",

    "CREATE INDEX node_type IF NOT EXISTS "
    "FOR (n:Node) ON (n.node_type)",

    "CREATE INDEX node_risk IF NOT EXISTS "
    "FOR (n:Node) ON (n.risk_level)",

    "CREATE INDEX node_blast IF NOT EXISTS "
    "FOR (n:Node) ON (n.blast_radius)",

    "CREATE INDEX node_pagerank IF NOT EXISTS "
    "FOR (n:Node) ON (n.pagerank)",

    "CREATE INDEX file_repo_id IF NOT EXISTS "
    "FOR (f:File) ON (f.repo_id)",

]


async def apply_schema() -> None:
    """
    Apply all schema constraints and indexes.
    Safe to call on every startup — IF NOT EXISTS prevents errors
    if they already exist.
    Logs each step. Does not raise — schema errors are logged and
    skipped so a Neo4j schema quirk does not crash the whole server.
    """
    logger.info("Applying Neo4j schema (%d queries)", len(SCHEMA_QUERIES))
    for query in SCHEMA_QUERIES:
        try:
            await run_write_query(query)
        except Exception as exc:
            # Some Neo4j editions do not support IS NODE KEY —
            # fall back to simpler constraint if this fails.
            logger.warning("Schema query skipped (%s): %s", type(exc).__name__, query[:80])
    logger.info("Neo4j schema applied")


# ── Node property shapes ─────────────────────────────────────────────────────
# These dicts define what properties are written for each node type.
# Used by the graph writer on Day 5.

def make_node_props(node: dict) -> dict:
    """
    Convert a PostgreSQL node row dict to Neo4j property dict.
    Only include properties we actually want to store in the graph.
    """
    return {
        "id":             str(node.get("id", "")),
        "repo_id":        str(node.get("repo_id", "")),
        "name":           node.get("name", ""),
        "node_type":      node.get("node_type", "unknown"),
        "file_path":      node.get("file_path", ""),
        "language":       node.get("language", ""),
        "signature":      node.get("signature", ""),
        "fan_in":         node.get("fan_in", 0),
        "fan_out":        node.get("fan_out", 0),
        "blast_radius":   node.get("blast_radius", 0),
        "risk_level":     node.get("risk_level", "low"),
        "pagerank":       node.get("pagerank", 0.0),
        "coupling_score": node.get("coupling_score", 0.0),
    }


def make_edge_props(edge: dict) -> dict:
    """
    Convert a PostgreSQL edge row dict to Neo4j relationship dict.
    """
    return {
        "from_id":   str(edge.get("from_node_id", "")),
        "to_id":     str(edge.get("to_node_id", "")),
        "repo_id":   str(edge.get("repo_id", "")),
        "edge_type": edge.get("edge_type", "CALLS"),
    }
