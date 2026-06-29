import logging
from neo4j import AsyncGraphDatabase, AsyncDriver
from app.config import get_settings

logger = logging.getLogger(__name__)

_driver: AsyncDriver | None = None


async def get_driver() -> AsyncDriver:
    """
    Return the shared Neo4j async driver instance.
    Creates it on first call (lazy initialization).
    Forces bolt://127.0.0.1:7687 to avoid IPv6 connection issues on Windows.
    """
    global _driver
    if _driver is None:
        settings = get_settings()

        # Force IPv4 by replacing localhost or neo4j:// with bolt://127.0.0.1
        # Windows resolves localhost to ::1 (IPv6) first which Neo4j rejects
        uri = settings.neo4j_uri
        if uri.startswith("neo4j://localhost") or uri.startswith("bolt://localhost"):
            uri = uri.replace("localhost", "127.0.0.1")
        if uri.startswith("neo4j://127.0.0.1"):
            uri = uri.replace("neo4j://", "bolt://")
        if not uri.startswith("bolt://"):
            uri = "bolt://127.0.0.1:7687"

        _driver = AsyncGraphDatabase.driver(
            uri,
            auth=(settings.neo4j_user, settings.neo4j_password),
            max_connection_pool_size=50,
            connection_timeout=10.0,
        )
        logger.info("Neo4j driver initialized (uri=%s)", uri)
    return _driver


async def close_driver() -> None:
    """Close the driver. Call during FastAPI shutdown."""
    global _driver
    if _driver:
        await _driver.close()
        _driver = None
        logger.info("Neo4j driver closed")


async def verify_connectivity() -> bool:
    """
    Verify Neo4j is reachable. Returns True on success, False on failure.
    Logs clearly either way. Does NOT raise — safe to call at startup
    even if Neo4j is temporarily unavailable.
    """
    try:
        driver = await get_driver()
        await driver.verify_connectivity()
        logger.info("Neo4j connectivity verified")
        return True
    except Exception as exc:
        logger.error("Neo4j connectivity failed: %s", exc)
        return False


async def run_query(cypher: str, parameters: dict | None = None) -> list[dict]:
    """
    Execute a read Cypher query.
    Returns a list of record dicts (empty list if no results).
    Raises on query error — caller handles exceptions.
    """
    driver = await get_driver()
    async with driver.session() as session:
        result = await session.run(cypher, parameters or {})
        records = await result.data()
        return records


async def run_write_query(cypher: str, parameters: dict | None = None) -> list[dict]:
    """
    Execute a write Cypher query inside an auto-committed transaction.
    Returns result records as list of dicts.
    Raises on error — caller handles exceptions.
    """
    driver = await get_driver()
    async with driver.session() as session:
        result = await session.run(cypher, parameters or {})
        records = await result.data()
        return records


async def run_write_batch(
    cypher: str,
    batch: list[dict],
    batch_size: int = 500,
) -> int:
    """
    Execute a write query for a large list of parameter dicts.
    Uses UNWIND so one Cypher call handles batch_size rows.
    Returns total rows written.

    Usage:
        await run_write_batch(
            "UNWIND $rows AS row "
            "MERGE (n:Node {id: row.id, repo_id: row.repo_id}) "
            "SET n += row",
            rows_list,
        )
    """
    driver = await get_driver()
    total = 0
    async with driver.session() as session:
        for i in range(0, len(batch), batch_size):
            chunk = batch[i : i + batch_size]
            await session.run(cypher, {"rows": chunk})
            total += len(chunk)
    return total