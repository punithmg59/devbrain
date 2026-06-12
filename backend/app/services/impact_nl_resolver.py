import re
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

STOP_WORDS = frozenset(
    """
    a an the what if i change modify remove delete update fix break happens
    depends on which features use can safely will would should my this that
    when where how why who is are was were be been being have has had do does
    did doing would could should may might must shall
    """.split()
)

DOMAIN_EXPANSIONS: dict[str, list[str]] = {
    "login": ["auth", "oauth", "session", "github", "callback", "token"],
    "oauth": ["auth", "github", "callback", "session", "token"],
    "github": ["oauth", "auth", "repo", "connect", "callback"],
    "auth": ["oauth", "session", "login", "token", "middleware"],
    "authentication": ["auth", "oauth", "session", "login"],
    "session": ["auth", "cookie", "token", "middleware"],
    "redis": ["cache", "redis_client", "session"],
    "database": ["db", "postgres", "sqlalchemy", "session"],
    "api": ["route", "endpoint", "router"],
    "repository": ["repo", "connect", "analyze", "github"],
    "analysis": ["analyze", "parser", "pipeline"],
    "delete": ["remove", "disconnect"],
    "remove": ["delete", "disconnect"],
}


def tokenize_query(query: str) -> list[str]:
    raw = re.findall(r"[a-zA-Z0-9_./-]+", query.lower())
    tokens = [t for t in raw if len(t) > 1 and t not in STOP_WORDS]
    expanded: list[str] = []
    seen: set[str] = set()
    for t in tokens:
        if t not in seen:
            expanded.append(t)
            seen.add(t)
        for extra in DOMAIN_EXPANSIONS.get(t, []):
            if extra not in seen:
                expanded.append(extra)
                seen.add(extra)
    return expanded[:12]


def _row_dict(row) -> dict:
    d = dict(row)
    if isinstance(d.get("id"), UUID):
        d["id"] = str(d["id"])
    return d


class ImpactNLResolver:
    async def resolve(
        self,
        query: str,
        repo_id: str,
        db: AsyncSession,
        *,
        natural_language: bool = True,
    ) -> tuple[dict | None, list[dict], float]:
        """
        Returns (best_source_node, matched_entities, confidence).
        """
        q = query.strip()
        if not q:
            return None, [], 0.0

        if not natural_language and len(q.split()) <= 3:
            exact = await self._exact_lookup(q, repo_id, db)
            if exact:
                return exact, [self._entity(exact, "Exact name match", 1.0)], 1.0

        tokens = tokenize_query(q) if natural_language else [q.lower()]
        if not tokens:
            tokens = [q.lower()]

        candidates = await self._search_candidates(tokens, q, repo_id, db)
        if not candidates:
            exact = await self._exact_lookup(q, repo_id, db)
            if exact:
                return exact, [self._entity(exact, "Exact name match", 1.0)], 0.95
            return None, [], 0.0

        best = candidates[0]
        confidence = min(0.98, best["score"])
        entities = [
            self._entity(c, c["match_reason"], c["score"])
            for c in candidates[:5]
        ]
        source = {
            "id": best["id"],
            "name": best["name"],
            "node_type": best["node_type"],
            "file_path": best.get("file_path") or "",
            "start_line": best.get("start_line"),
            "end_line": best.get("end_line"),
            "http_method": best.get("http_method"),
            "route_path": best.get("route_path"),
            "summary": best.get("summary"),
        }
        return source, entities, confidence

    def _entity(self, row: dict, reason: str, score: float) -> dict:
        return {
            "id": row["id"],
            "name": row["name"],
            "node_type": row["node_type"],
            "file_path": row.get("file_path") or "",
            "match_reason": reason,
            "score": round(score, 3),
        }

    async def _exact_lookup(
        self, query: str, repo_id: str, db: AsyncSession
    ) -> dict | None:
        sql = text("""
            SELECT n.id, n.name, n.node_type,
                   COALESCE(rf.file_path, n.full_path) as file_path,
                   n.start_line, n.end_line,
                   n.http_method, n.route_path, n.summary
            FROM nodes n
            LEFT JOIN repo_files rf ON n.file_id = rf.id
            WHERE n.repo_id = :repo_id
            AND (LOWER(n.name) = LOWER(:query)
                 OR rf.file_path ILIKE :path_pattern)
            LIMIT 1
        """)
        result = await db.execute(
            sql,
            {
                "repo_id": repo_id,
                "query": query,
                "path_pattern": f"%{query}%",
            },
        )
        row = result.mappings().first()
        return _row_dict(row) if row else None

    async def _search_candidates(
        self,
        tokens: list[str],
        full_query: str,
        repo_id: str,
        db: AsyncSession,
    ) -> list[dict]:
        patterns = [f"%{t}%" for t in tokens]
        full_pattern = f"%{full_query}%"

        sql = text("""
            SELECT n.id, n.name, n.node_type,
                   COALESCE(rf.file_path, n.full_path) as file_path,
                   n.start_line, n.end_line,
                   n.http_method, n.route_path, n.summary,
                   n.tags,
                   CASE
                     WHEN LOWER(n.name) = LOWER(:full_query) THEN 100
                     WHEN n.name ILIKE :full_pattern THEN 80
                     WHEN n.node_type = 'api_route' AND (
                       n.route_path ILIKE :full_pattern
                       OR COALESCE(n.http_method, '') ILIKE :full_pattern
                     ) THEN 75
                     WHEN rf.file_path ILIKE :full_pattern THEN 70
                     WHEN n.summary ILIKE :full_pattern THEN 55
                     ELSE 40
                   END as base_score
            FROM nodes n
            LEFT JOIN repo_files rf ON n.file_id = rf.id
            WHERE n.repo_id = :repo_id
            AND (
                n.name ILIKE ANY(:patterns)
                OR rf.file_path ILIKE ANY(:patterns)
                OR n.route_path ILIKE ANY(:patterns)
                OR n.summary ILIKE ANY(:patterns)
                OR n.full_path ILIKE ANY(:patterns)
                OR EXISTS (
                    SELECT 1 FROM unnest(COALESCE(n.tags, ARRAY[]::text[])) t
                    WHERE t ILIKE ANY(:patterns)
                )
            )
            LIMIT 25
        """)
        try:
            result = await db.execute(
                sql,
                {
                    "repo_id": repo_id,
                    "full_query": full_query,
                    "full_pattern": full_pattern,
                    "patterns": patterns,
                },
            )
        except Exception:
            result = await db.execute(
                text("""
                    SELECT n.id, n.name, n.node_type,
                           COALESCE(rf.file_path, n.full_path) as file_path,
                           n.start_line, n.end_line,
                           n.http_method, n.route_path, n.summary,
                           50 as base_score
                    FROM nodes n
                    LEFT JOIN repo_files rf ON n.file_id = rf.id
                    WHERE n.repo_id = :repo_id
                    AND (
                        n.name ILIKE :full_pattern
                        OR rf.file_path ILIKE :full_pattern
                    )
                    LIMIT 15
                """),
                {"repo_id": repo_id, "full_pattern": full_pattern},
            )

        scored: list[dict] = []
        for row in result.mappings():
            d = _row_dict(row)
            token_hits = sum(
                1
                for t in tokens
                if t in d["name"].lower()
                or t in (d.get("file_path") or "").lower()
                or t in (d.get("route_path") or "").lower()
                or t in (d.get("summary") or "").lower()
            )
            type_bonus = 15 if d["node_type"] == "api_route" else 0
            score = (d.get("base_score", 40) + token_hits * 8 + type_bonus) / 100.0
            d["score"] = min(0.99, score)
            d["match_reason"] = self._reason(d, tokens)
            scored.append(d)

        scored.sort(key=lambda x: x["score"], reverse=True)
        return scored

    def _reason(self, row: dict, tokens: list[str]) -> str:
        if row["node_type"] == "api_route" and row.get("route_path"):
            return f"API route matched: {row.get('http_method', 'GET')} {row['route_path']}"
        path = row.get("file_path") or ""
        for t in tokens:
            if t in row["name"].lower():
                return f"Function/class name contains '{t}'"
            if t in path.lower():
                return f"File path contains '{t}'"
        if row.get("summary"):
            return "Matched node summary text"
        return "Semantic keyword match in codebase graph"
