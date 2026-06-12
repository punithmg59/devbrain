"""Graph path utility service for evidence chain construction."""

from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


class GraphPathService:
    async def shortest_path_between_nodes(
        self,
        repo_id: str,
        source_id: str,
        target_ids: list[str],
        db: AsyncSession,
    ) -> list[str]:
        if not source_id or not target_ids:
            return []

        sql = text(
            """
            WITH RECURSIVE search AS (
                SELECT
                    from_node_id::text AS current_node,
                    to_node_id::text AS next_node,
                    ARRAY[from_node_id::text, to_node_id::text] AS path,
                    1 AS depth
                FROM edges
                WHERE repo_id = :repo_id
                  AND from_node_id = :source_id
                UNION ALL
                SELECT
                    e.from_node_id::text AS current_node,
                    e.to_node_id::text AS next_node,
                    s.path || e.to_node_id::text AS path,
                    s.depth + 1 AS depth
                FROM edges e
                JOIN search s ON e.from_node_id::text = s.next_node
                WHERE e.repo_id = :repo_id
                  AND e.to_node_id::text <> ALL(s.path)
                  AND s.depth < 12
            )
            SELECT path
            FROM search
            WHERE next_node = ANY(:target_ids)
            ORDER BY depth ASC
            LIMIT 1
            """
        )
        result = await db.execute(
            sql,
            {
                "repo_id": repo_id,
                "source_id": source_id,
                "target_ids": target_ids,
            },
        )
        row = result.mappings().first()
        if not row:
            return []
        return list(row["path"] or [])
