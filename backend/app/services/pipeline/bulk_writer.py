import logging
from datetime import datetime, timezone
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


async def bulk_upsert_nodes(
    db: AsyncSession,
    nodes: list[dict],
    repo_id: str,
) -> int:
    """
    Bulk upsert nodes into PostgreSQL nodes table.

    Uses INSERT ... ON CONFLICT (id) DO UPDATE so re-running
    analysis updates existing rows rather than failing.

    Read the Node model to get exact column names.
    Common columns: id, repo_id, name, node_type, file_path,
                    language, signature, line_start, line_end

    Returns count of rows upserted.
    """
    if not nodes:
        return 0

    # Build rows from parsed node dicts
    # Adjust column names to match your actual Node model
    rows = []
    for node in nodes:
        rows.append({
            "id":         str(node.get("id", "")),
            "repo_id":    str(repo_id),
            "name":       str(node.get("name", ""))[:1000],
            "node_type":  str(node.get("node_type", "unknown"))[:50],
            "file_path":  str(node.get("file_path", ""))[:2000],
            "language":   str(node.get("language", ""))[:100],
            "signature":  str(node.get("signature", ""))[:1000],
            "start_line": int(node.get("start_line") or 0),
            "end_line":   int(node.get("end_line") or 0),
        })

    if not rows:
        return 0

    # Build bulk upsert — adjust table name and columns to match your model
    # Read your Node model table name with Node.__tablename__
    stmt = text("""
        INSERT INTO nodes
            (id, repo_id, name, node_type, file_path,
             language, signature, start_line, end_line)
        VALUES
            (:id, :repo_id, :name, :node_type, :file_path,
             :language, :signature, :start_line, :end_line)
        ON CONFLICT (id) DO UPDATE SET
            name       = EXCLUDED.name,
            node_type  = EXCLUDED.node_type,
            file_path  = EXCLUDED.file_path,
            language   = EXCLUDED.language,
            signature  = EXCLUDED.signature,
            start_line = EXCLUDED.start_line,
            end_line   = EXCLUDED.end_line
    """)

    await db.execute(stmt, rows)
    await db.commit()

    logger.info("PostgreSQL: upserted %d nodes for repo %s", len(rows), repo_id)
    return len(rows)


async def bulk_upsert_edges(
    db: AsyncSession,
    edges: list[dict],
    repo_id: str,
) -> int:
    """
    Bulk upsert edges into PostgreSQL edges table.

    Read the Edge model for exact column names.
    Common columns: id, repo_id, from_node_id, to_node_id, edge_type

    Returns count of rows upserted.
    """
    if not edges:
        return 0

    rows = []
    for edge in edges:
        from_id = str(edge.get("from_node_id", ""))
        to_id = str(edge.get("to_node_id", ""))
        if not from_id or not to_id:
            continue
        rows.append({
            "id":           str(edge.get("id", "")),
            "repo_id":      str(repo_id),
            "from_node_id": from_id,
            "to_node_id":   to_id,
            "edge_type":    str(edge.get("edge_type", "CALLS"))[:50],
        })

    if not rows:
        return 0

    # Adjust table name and columns to match your Edge model
    stmt = text("""
        INSERT INTO edges
            (id, repo_id, from_node_id, to_node_id, edge_type)
        VALUES
            (:id, :repo_id, :from_node_id, :to_node_id, :edge_type)
        ON CONFLICT (id) DO UPDATE SET
            edge_type = EXCLUDED.edge_type
    """)

    await db.execute(stmt, rows)
    await db.commit()

    logger.info("PostgreSQL: upserted %d edges for repo %s", len(rows), repo_id)
    return len(rows)


async def update_file_hashes(
    db: AsyncSession,
    file_hashes: list[dict],
    repo_id: str,
) -> None:
    """
    Update content_hash and last_analyzed_at on repo_files rows
    after successful parsing. This is what enables incremental
    analysis on the next run.

    file_hashes: list of dicts with keys: file_path, content_hash
    """
    if not file_hashes:
        return

    now = datetime.now(timezone.utc)

    stmt = text("""
        UPDATE repo_files
        SET content_hash     = :content_hash,
            last_analyzed_at = :analyzed_at
        WHERE repo_id  = :repo_id
        AND   file_path = :file_path
    """)

    rows = [
        {
            "repo_id":      str(repo_id),
            "file_path":    f["file_path"],
            "content_hash": f["content_hash"],
            "analyzed_at":  now,
        }
        for f in file_hashes
        if f.get("file_path") and f.get("content_hash")
    ]

    if rows:
        await db.execute(stmt, rows)
        await db.commit()
        logger.info(
            "Updated content hashes for %d files in repo %s",
            len(rows), repo_id
        )
